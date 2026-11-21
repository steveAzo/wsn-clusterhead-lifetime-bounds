"""Compute the data behind the trace figures (results/fig_data/*.json). Serial and light; run once.
Usage (from Paper5/): python -I src/paper/fig_data.py alive|residual|cg
  alive:    alive (and connected) nodes per round for DIRECT, LEACH, KMRE, PSO-C (k = 5), layout 0, FO centre and CC2420 edge,
            until 90% of the nodes are dead or disconnected; uplinks are recomputed after each death.
  residual: residual energy of every node at the first node death, FO centre layout 0, four protocols and the LP schedule.
  cg:       LB and UB per column-generation iteration, layout 0, FO centre and CC2420 centre.
"""
import json
import os
import sys

import numpy as np
from scipy.optimize import linprog

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scoping"))
import e8_model_v2 as v2  # noqa: E402
import e2_lifetime_gate as e2  # noqa: E402

OUT = os.path.join(HERE, "..", "..", "results", "fig_data")
os.makedirs(OUT, exist_ok=True)


def layout(seed):
    return np.random.default_rng(100 + seed).uniform(0, 100, (100, 2))


def connected_uplinks(m, pos, sink, alive):
    """Recompute uplinks; nodes that can no longer reach the sink are dropped (counted as lost)."""
    while True:
        U = v2.uplinks(m, pos, sink, alive)
        bad = alive & ~np.isfinite(U).all(1)
        if not bad.any():
            return U, alive
        alive = alive & ~bad


def run(strategy, m, pos, sink, seed, k=5, E0=0.5, stop_frac=0.1, max_rounds=8000, want_fnd_energy=False):
    rng = np.random.default_rng(11 + seed)
    n = len(pos)
    E = np.full(n, E0)
    alive = np.ones(n, bool)
    last_ch = np.full(n, -10**9)
    U, alive = connected_uplinks(m, pos, sink, alive)
    cent = pos[rng.choice(n, k, replace=False)]
    for _ in range(50):
        lab = np.linalg.norm(pos[:, None] - cent[None], axis=2).argmin(1)
        cent = np.array([pos[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(k)])
    p = 0.05
    trace = [(0, int(alive.sum()))]
    fnd_E = None
    for r in range(max_rounds):
        if strategy == "DIRECT":
            chs = []
        elif strategy == "LEACH":
            epoch = int(round(1 / p))
            thr = p / (1 - p * (r % epoch))
            chs = list(np.flatnonzero(alive & (r - last_ch >= epoch) & (rng.random(n) < thr)))
        elif strategy == "KMRE":
            chs = [int(np.flatnonzero(alive & (lab == j))[E[alive & (lab == j)].argmax()]) for j in np.unique(lab[alive])]
        else:
            al = np.flatnonzero(alive)

            def fit(ch):
                d = np.linalg.norm(pos[al, None] - pos[None, ch], axis=2)
                a = d.argmin(1)
                md = max(d[a == j, j].mean() for j in range(len(ch)) if (a == j).any())
                return 0.5 * md + 0.5 * (E[al].sum() / E[ch].sum())
            chs = e2.pso(pos, sink, alive, E, min(k, int(alive.sum())), fit, rng)
        chs = [c for c in chs if alive[c]]
        last_ch[chs] = r
        c = v2.charges(m, pos, sink, alive, chs, U)
        E = E - np.where(alive, c, 0.0)
        died = alive & (E <= 0)
        if died.any():
            if fnd_E is None:
                fnd_E = (r + 1, np.maximum(E, 0).tolist())
                if want_fnd_energy:
                    return fnd_E
            alive = alive & ~died
            U, alive = connected_uplinks(m, pos, sink, alive)
            trace.append((r + 1, int(alive.sum())))
            if alive.sum() <= stop_frac * n:
                break
    return trace


def lp_schedule_fnd_energy(m, pos, sink, R=50, iters=600, reiters=20):
    """E10 logic (exact reports), returning the FND round and the residual energies at that moment."""
    sys.path.insert(0, os.path.join(HERE, "..", "scoping"))
    import e10_lp_protocol as e10
    n = len(pos)
    U = v2.uplinks(m, pos, sink, np.ones(n, bool))
    E = np.full(n, 0.5)
    cols = [U.sum(0)]
    nrng = np.random.default_rng(7)
    r = 0
    while True:
        b = E * (1 + 0.0 * nrng.standard_normal(n))  # same random stream as e10 (noise 0), so the FND matches results
        x, val = e10.plan(m, pos, sink, U, b, cols, iters if r == 0 else reiters, nrng)
        E -= m.erx_ctrl * 4
        if val < 1:
            seq = [int(np.argmax(x))]
        else:
            w = x / x.sum() * R
            cnt = np.floor(w).astype(int)
            cnt[np.argsort(-(w - cnt))[:R - cnt.sum()]] += 1
            seq = [c for c in np.flatnonzero(cnt) for _ in range(cnt[c])]
            nrng.shuffle(seq)
        for c in seq:
            E -= cols[c]
            r += 1
            if (E <= 0).any():
                return r, np.maximum(E, 0).tolist()


def cg_trace(m, pos, sink, iters=800, tol=0.02, warm=300, seed=0):
    """lp_bound of e8_model_v2 with a per-iteration record of (LB, UB)."""
    n, E0 = len(pos), 0.5
    U = v2.uplinks(m, pos, sink, np.ones(n, bool))
    cols = [v2.charges(m, pos, sink, np.ones(n, bool), [], U)]
    wr = np.random.default_rng(seed)
    for k in (2, 3, 5, 8, 12, 20):
        cent = pos[wr.choice(n, k, replace=False)]
        for _ in range(30):
            lab = np.linalg.norm(pos[:, None] - cent[None], axis=2).argmin(1)
            cent = np.array([pos[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(k)])
        for _ in range(warm // 6):
            chs = [int(wr.choice(np.flatnonzero(lab == j))) for j in range(k) if (lab == j).any()]
            cols.append(v2.charges(m, pos, sink, np.ones(n, bool), chs, U))
    pm1, _ = v2.price_v2(np.ones(n), m, pos, sink, U)
    ub = n * E0 / pm1
    yb, alpha, tr = None, 0.7, []
    for it in range(iters):
        A = np.array(cols).T
        res = linprog(-np.ones(A.shape[1]), A_ub=A, b_ub=np.full(n, E0), bounds=(0, None), method="highs")
        lb = -res.fun
        ylp = -res.ineqlin.marginals
        y = ylp if yb is None else alpha * yb + (1 - alpha) * ylp
        pm, col = v2.price_v2(y, m, pos, sink, U)
        if E0 * y.sum() / pm < ub:
            ub, yb = E0 * y.sum() / pm, y.copy()
        elif yb is None:
            yb = y.copy()
        if ylp @ col >= 1 - 1e-9:
            pm2, col = v2.price_v2(ylp, m, pos, sink, U)
            if E0 * ylp.sum() / pm2 < ub:
                ub, yb = E0 * ylp.sum() / pm2, ylp.copy()
        tr.append((it, lb, ub))
        if ub / lb - 1 < tol:
            break
        cols.append(col)
    return tr


def main():
    job = sys.argv[1]
    if job == "alive":
        out = {}
        for name, s in [("FO", "centre"), ("CC2420", "edge")]:
            m, pos, sink = v2.Model(name), layout(0), np.array(v2.SINKS[s])
            for st in ("DIRECT", "LEACH", "KMRE", "PSOC"):
                out[f"{name} {s} {st}"] = run(st, m, pos, sink, 0)
                print(name, s, st, out[f"{name} {s} {st}"][1][0], out[f"{name} {s} {st}"][-1], flush=True)
        json.dump(out, open(os.path.join(OUT, "alive.json"), "w"))
    elif job == "residual":
        m, pos, sink = v2.Model("FO"), layout(0), np.array(v2.SINKS["centre"])
        out = {}
        for st in ("DIRECT", "LEACH", "KMRE", "PSOC"):
            out[st] = run(st, m, pos, sink, 0, want_fnd_energy=True)
            print(st, out[st][0], flush=True)
        out["LP"] = lp_schedule_fnd_energy(m, pos, sink)
        print("LP", out["LP"][0], flush=True)
        json.dump(out, open(os.path.join(OUT, "residual.json"), "w"))
    elif job == "cg":
        out = {}
        for name, s in [("FO", "centre"), ("CC2420", "centre")]:
            m, pos, sink = v2.Model(name), layout(0), np.array(v2.SINKS[s])
            out[f"{name} {s}"] = cg_trace(m, pos, sink)
            print(name, s, len(out[f"{name} {s}"]), out[f"{name} {s}"][-1], flush=True)
        json.dump(out, open(os.path.join(OUT, "cg.json"), "w"))


if __name__ == "__main__":
    main()
