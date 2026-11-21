"""E2 gate (idea 3 reframe): lifetime headroom of swarm cluster-head selection over a zero-compute rule.

Strategies per round (perfect aggregation at CHs, LEACH setting; relay cost beyond radio range charged to the CH):
  DIRECT  every node sends to the sink.
  LEACH   classic threshold rule, p = 0.05.
  KMRE    k-means clusters fixed once (k chosen by the energy model on full batteries); each round the
          alive node with the most residual energy in each cluster is CH. No per-round search.
  PSOC    PSO-C (Latiff et al. 2007): 20 particles, 30 iterations, fitness 0.5*max mean intra-cluster distance
          + 0.5*(sum E_alive / sum E_CH); candidates = alive nodes with E >= mean.
  PSOE    energy-aware swarm: same PSO, fitness = max over nodes of (round charge / residual energy), i.e. it
          directly minimises the fastest-dying node. Best case for a metaheuristic.
Bound: FND <= sum(E0) / E_min_round, with E_min_round from E1-style local search (valid until first death).
Usage: python -I src/scoping/e2_lifetime_gate.py [model ...]   models: FO CC2420 nRF52840 CC1101-868
"""
import math
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from e1_radio_model_gate import (D0, E_DA, E_ELEC, E_FS, E_MP, K_BITS, MARGIN, PL_N,  # noqa: E402
                                 RADIOS, optimise)

sys.stdout.reconfigure(encoding="utf-8")


def model(name):
    """Return vectorised tx(d) [J per packet], erx [J], agg [J per packet aggregated]."""
    if name == "FO":
        def tx(d):
            d = np.asarray(d, float)
            return K_BITS * (E_ELEC + np.where(d < D0, E_FS * d**2, E_MP * d**4))
        return tx, K_BITS * E_ELEC, K_BITS * E_DA
    r = [x for x in RADIOS if x[0] == name][0]
    _, rate, v, irx, levels, sens, pl0 = r
    t = K_BITS / rate
    erx = irx * 1e-3 * v * t
    p = np.array([lv[0] for lv in levels], float)
    e = np.array([lv[1] for lv in levels], float) * 1e-3 * v * t
    rmax = 10 ** ((p[-1] - sens - MARGIN - pl0) / (10 * PL_N))

    def tx(d):
        d = np.maximum(np.asarray(d, float), 1.0)
        h = np.maximum(1, np.ceil(d / rmax))
        need = pl0 + 10 * PL_N * np.log10(d / h)
        idx = np.searchsorted(p - sens - MARGIN, need)  # first level whose budget >= need
        idx = np.minimum(idx, len(p) - 1)
        return h * e[idx] + (h - 1) * erx
    return tx, erx, 0.0


def charges(pos, sink, alive, chs, tx, erx, agg):
    """Per-node energy charged this round (array over all nodes; dead nodes 0)."""
    n = len(pos)
    c = np.zeros(n)
    al = np.flatnonzero(alive)
    if len(chs) == 0:
        c[al] = tx(np.linalg.norm(pos[al] - sink, axis=1))
        return c
    chs = np.asarray(chs)
    d = np.linalg.norm(pos[al, None, :] - pos[None, chs, :], axis=2)
    a = d.argmin(1)
    c[al] = tx(d[np.arange(len(al)), a]) + 0.0
    members = np.bincount(a, minlength=len(chs))  # includes CH itself (its distance 0)
    c[chs] = (members - 1) * erx + agg * members + tx(np.linalg.norm(pos[chs] - sink, axis=1))
    return c


def pso(pos, sink, alive, E, k, fitness, rng, parts=20, iters=30):
    cand = np.flatnonzero(alive & (E >= E[alive].mean()))
    if len(cand) < k:
        cand = np.flatnonzero(alive)
    k = min(k, len(cand))
    lo, hi = pos[cand].min(0), pos[cand].max(0)
    x = rng.uniform(lo, hi, (parts, k, 2))
    v = np.zeros_like(x)
    snap = lambda xx: np.unique(cand[np.linalg.norm(pos[cand][None, :, :] - xx[:, None, :], axis=2).argmin(1)])  # noqa: E731
    f = np.array([fitness(snap(xi)) for xi in x])
    pb, pf = x.copy(), f.copy()
    g = pb[pf.argmin()].copy()
    for it in range(iters):
        w = 0.9 - 0.5 * it / iters
        r1, r2 = rng.random(x.shape), rng.random(x.shape)
        v = w * v + 2 * r1 * (pb - x) + 2 * r2 * (g - x)
        x = np.clip(x + v, lo, hi)
        f = np.array([fitness(snap(xi)) for xi in x])
        better = f < pf
        pb[better], pf[better] = x[better], f[better]
        g = pb[pf.argmin()].copy()
    return list(snap(g))


def run(strategy, pos, sink, E0, tx, erx, agg, k, km_labels, rng, max_rounds=20000):
    n = len(pos)
    E = np.full(n, E0)
    alive = np.ones(n, bool)
    last_ch = np.full(n, -10**9)
    fnd = hnd = None
    labels = None
    p = 0.05
    for r in range(max_rounds):
        if strategy == "DIRECT":
            chs = []
        elif strategy == "LEACH":
            epoch = int(round(1 / p))
            thr = p / (1 - p * (r % epoch))
            elig = alive & (r - last_ch >= epoch)
            chs = list(np.flatnonzero(elig & (rng.random(n) < thr)))
        elif strategy == "KMRE":
            chs = []
            for j in np.unique(km_labels[alive]):
                m = np.flatnonzero(alive & (km_labels == j))
                chs.append(int(m[E[m].argmax()]))
        elif strategy == "KMRW":
            if r % 50 == 0:
                al0 = np.flatnonzero(alive)
                kk = min(k, len(al0))
                cent = pos[al0[np.linspace(0, len(al0) - 1, kk).astype(int)]]
                for _ in range(30):
                    lab = np.linalg.norm(pos[al0][:, None] - cent[None], axis=2).argmin(1)
                    cent = np.array([pos[al0][lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(kk)])
                labels = np.full(n, -1)
                labels[al0] = lab
            chs = []
            for j in np.unique(labels[alive & (labels >= 0)]):
                m = np.flatnonzero(alive & (labels == j))
                cost = (len(m) - 1) * erx + agg * len(m) + tx(np.linalg.norm(pos[m] - sink, axis=1))
                cost = cost + tx(np.linalg.norm(pos[m][:, None] - pos[m][None], axis=2)).sum(1) * 0  # members pay own tx
                chs.append(int(m[(E[m] / cost).argmax()]))
        else:
            al = np.flatnonzero(alive)
            if strategy == "PSOC":
                def fit(ch):
                    d = np.linalg.norm(pos[al, None] - pos[None, ch], axis=2)
                    a = d.argmin(1)
                    md = max(d[a == j, j].mean() for j in range(len(ch)) if (a == j).any())
                    return 0.5 * md + 0.5 * (E[al].sum() / E[ch].sum())
            else:
                def fit(ch):
                    c = charges(pos, sink, alive, ch, tx, erx, agg)
                    return (c[al] / E[al]).max()
            chs = pso(pos, sink, alive, E, k, fit, rng)
        chs = [c for c in chs if alive[c]]
        last_ch[chs] = r
        E -= charges(pos, sink, alive, chs, tx, erx, agg)
        newly = alive & (E <= 0)
        alive &= ~newly
        dead = n - alive.sum()
        if fnd is None and dead >= 1:
            fnd = r + 1
        if hnd is None and dead >= n // 2:
            hnd = r + 1
            return fnd, hnd
    return fnd, hnd


STRATS = ("DIRECT", "LEACH", "KMRE", "KMRW", "PSOC", "PSOE")


def main():
    global STRATS
    if "--fast" in sys.argv:
        sys.argv.remove("--fast")
        STRATS = ("DIRECT", "KMRE", "KMRW")
    names = sys.argv[1:] or ["FO", "CC2420", "nRF52840", "CC1101-868"]
    rng = np.random.default_rng(7)
    pos = rng.uniform(0, 100, (100, 2))
    sink = np.array([50.0, 175.0])
    E0 = 0.5
    for name in names:
        tx, erx, agg = model(name)
        # bound and k from E1-style search on full batteries (scalar energy wrapper)
        txs = lambda d: float(tx(np.array([d]))[0])  # noqa: E731
        best_e, best_k = math.inf, 1
        for k in (1, 2, 3, 5, 8):
            _, e = optimise(pos, sink, k, txs, erx, agg, rng, starts=3, iters=300)
            if e < best_e:
                best_e, best_k = e, k
        e_direct = charges(pos, sink, np.ones(100, bool), [], tx, erx, agg).sum()
        emin = min(best_e, e_direct)
        bound = 100 * E0 / emin
        kk = best_k
        cent = pos[rng.choice(100, kk, replace=False)]
        for _ in range(50):
            lab = np.linalg.norm(pos[:, None] - cent[None], axis=2).argmin(1)
            cent = np.array([pos[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(kk)])
        print(f"\n=== {name}: k*={best_k}, min round energy {emin*1e3:.3f} mJ (direct {e_direct*1e3:.3f}), FND bound {bound:.0f} rounds")
        for s in STRATS:
            t0 = time.time()
            fnd, hnd = run(s, pos, sink, E0, tx, erx, agg, best_k, lab, np.random.default_rng(11))
            print(f"  {s:7s} FND {fnd!s:>6}  HND {hnd!s:>6}  FND/bound {fnd / bound if fnd else float('nan'):.3f}  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
