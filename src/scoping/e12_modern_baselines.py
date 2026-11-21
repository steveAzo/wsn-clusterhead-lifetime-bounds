"""E12: are the E8 gaps an artefact of a weak or mistuned baseline? (v2 energy model, same layouts and seeds as E8)

Adds:
  - GWO: grey-wolf optimiser over CH positions (snapped to above-average-energy nodes, as PSO-C), with the multi-objective
    fitness most common in the 2021-2026 audit sample: 0.4 x (mean CH-to-sink distance / field diagonal)
    + 0.3 x (mean member-to-CH distance / field diagonal) + 0.3 x (mean alive energy / mean CH energy).
  - PSOC and GWO each run with k in {3, 5, 8}; the best k per case is reported (the method gets its best tuning).
  - MMAX: model-aware greedy. Each round, GWO searches the CH set minimising max_i (energy charged to i / residual of i)
    under the exact v2 round costs, i.e. a round-by-round heuristic that knows the radio model. If MMAX nears the LP bound,
    the gap comes from fitness functions that ignore the radio model; if not, it is intrinsic to myopic per-round choice.
Output line: M12 <model> <sink> seed <s>: PSOC_k3= PSOC_k5= PSOC_k8= GWO_k3= GWO_k5= GWO_k8= MMAX=
Compare with LP bracket and DIRECT/LEACH/KMRE in results/e8_v2.txt.
Usage: python -I src/scoping/e12_modern_baselines.py <model> <sink> <seed>
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e8_model_v2 as v2  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def fast_charges(m, pos, sink, al, chs, U, txd):
    """Vectorised v2 round charges (equals v2.charges; checked in --check)."""
    n = len(pos)
    e = np.zeros(n)
    chs = np.asarray(chs)
    d = txd["D"][np.ix_(al, chs)]
    a = d.argmin(1)
    dmin = d[np.arange(len(al)), a]
    tgt = chs[a]
    mem = al != tgt
    inr = mem & (dmin <= m.rmax)
    out = mem & ~inr
    e[al[inr]] += txd["T"][al[inr], tgt[inr]]
    np.add.at(e, tgt[inr], m.erx + m.agg)
    if out.any():
        e += U[al[out]].sum(0)
    e += U[chs].sum(0)
    e[chs] += m.agg + m.etx_ctrl
    e[al] += m.erx_ctrl
    return e


def gwo(cand, pos, k, fitness, rng, wolves=20, iters=30):
    k = min(k, len(cand))
    lo, hi = pos[cand].min(0), pos[cand].max(0)
    snap = lambda xx: np.unique(cand[np.linalg.norm(pos[cand][None] - xx[:, None], axis=2).argmin(1)])  # noqa: E731
    x = rng.uniform(lo, hi, (wolves, k, 2))
    f = np.array([fitness(snap(xi)) for xi in x])
    for it in range(iters):
        o = np.argsort(f)[:3]
        A_, B_, D_ = x[o[0]].copy(), x[o[1]].copy(), x[o[2]].copy()
        a = 2 - 2 * it / iters
        new = np.zeros_like(x)
        for L in (A_, B_, D_):
            r1, r2 = rng.random(x.shape), rng.random(x.shape)
            A, C = 2 * a * r1 - a, 2 * r2
            new += L - A * np.abs(C * L - x)
        x = np.clip(new / 3, lo, hi)
        f2 = np.array([fitness(snap(xi)) for xi in x])
        f = f2
        best = snap(A_) if fitness(snap(A_)) <= f.min() else snap(x[f.argmin()])
    return list(best)


def simulate(strategy, k, m, pos, sink, rng, E0=0.5, max_rounds=20000):
    import e2_lifetime_gate as e2
    n = len(pos)
    E = np.full(n, E0)
    alive = np.ones(n, bool)
    U = v2.uplinks(m, pos, sink, alive)
    D = np.linalg.norm(pos[:, None] - pos[None], axis=2)
    txd = {"D": D, "T": m.tx(D)}
    diag = np.hypot(100, 100)
    dsink = np.linalg.norm(pos - sink, axis=1)
    for r in range(max_rounds):
        al = np.flatnonzero(alive)
        cand = np.flatnonzero(alive & (E >= E[alive].mean()))
        if len(cand) < k:
            cand = al
        if strategy == "PSOC":
            def fit(ch):
                d = D[np.ix_(al, ch)]
                a = d.argmin(1)
                md = max(d[a == j, j].mean() for j in range(len(ch)) if (a == j).any())
                return 0.5 * md + 0.5 * (E[al].sum() / E[ch].sum())
            chs = e2.pso(pos, sink, alive, E, k, fit, rng)
        elif strategy == "GWO":
            def fit(ch):
                d = D[np.ix_(al, ch)]
                return (0.4 * dsink[ch].mean() / diag + 0.3 * d.min(1).mean() / diag
                        + 0.3 * E[al].mean() / max(E[ch].mean(), 1e-12))
            chs = gwo(cand, pos, k, fit, rng)
        else:  # MMAX: model-aware, minimise the largest fraction of residual energy spent this round
            def fit(ch):
                e = fast_charges(m, pos, sink, al, np.asarray(ch), U, txd)
                return float(np.max(e[al] / E[al])) if np.isfinite(e).all() else np.inf
            best = None
            for kk in (2, 3, 5, 8):
                c = gwo(al, pos, kk, fit, rng, wolves=12, iters=15)
                if best is None or fit(c) < fit(best):
                    best = c
            ed = U[al].sum(0)  # DIRECT round is a candidate too
            if np.isfinite(ed).all() and np.max(ed[al] / E[al]) < fit(best):
                best = []
            chs = best
        c = v2.charges(m, pos, sink, alive, chs, U) if len(chs) == 0 else fast_charges(m, pos, sink, al, np.asarray(chs), U, txd)
        if not np.isfinite(c).all():
            return r
        E -= c
        if (E[alive] <= 0).any():
            return r + 1
    return max_rounds


def main():
    a = sys.argv[1:]
    name, sname, seed = a[0], a[1], int(a[2])
    m = v2.Model(name)
    rng0 = np.random.default_rng(100 + seed)
    pos = rng0.uniform(0, 100, (100, 2))
    sink = np.array(v2.SINKS[sname])
    if "--check" in a:
        U = v2.uplinks(m, pos, sink, np.ones(100, bool))
        D = np.linalg.norm(pos[:, None] - pos[None], axis=2)
        txd = {"D": D, "T": m.tx(D)}
        for chs in ([3, 40, 77], [5], list(range(0, 100, 9))):
            x = v2.charges(m, pos, sink, np.ones(100, bool), chs, U)
            y = fast_charges(m, pos, sink, np.arange(100), np.array(chs), U, txd)
            print("check", chs[:3], float(np.max(np.abs(x - y))))
        return
    out = {}
    for s in ("PSOC", "GWO"):
        for k in (3, 5, 8):
            out[f"{s}_k{k}"] = simulate(s, k, m, pos, sink, np.random.default_rng(11 + seed))
    out["MMAX"] = simulate("MMAX", 0, m, pos, sink, np.random.default_rng(11 + seed))
    print(f"M12 {name} {sname} seed {seed}: " + " ".join(f"{k}={v}" for k, v in out.items()), flush=True)


if __name__ == "__main__":
    main()
