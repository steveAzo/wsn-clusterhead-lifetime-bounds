"""E10: the LP schedule as a protocol (v2 energy model), versus PSO-C and the exact bound.

LPSCHED: every R rounds the sink solves the role-assignment LP (column generation, exact v2 pricing, capped iterations)
with b = reported residual energies (true energy x (1 + noise), noise ~ N(0, sigma) per node and report), turns the LP
solution x_c into an integer sequence for the next R rounds (largest-remainder apportionment over x_c / sum x), and
executes it with true energies. Control cost of the schedule broadcast is in the v2 per-round control term.
Output: FND rounds. Compare with results/e8_v2.txt (PSOC, LP bracket) for the same case.
Usage: python -I src/scoping/e10_lp_protocol.py <model> <sink> <seed> [--replan 50] [--noise 0.0] [--iters 200] [--reiters 20] (first plan uses --iters pricing steps, later re-plans --reiters on the pooled columns)
"""
import os
import sys

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e8_model_v2 as v2  # noqa: E402

v2.PRICE_TIME_LIMIT = 30  # protocol re-plans need good columns, not proofs

sys.stdout.reconfigure(encoding="utf-8")


def plan(m, pos, sink, U, b, cols, iters, rng):
    n = len(pos)
    for _ in range(iters):
        A = np.array(cols).T
        res = linprog(-np.ones(A.shape[1]), A_ub=A, b_ub=np.maximum(b, 1e-12), bounds=(0, None), method="highs")
        y = -res.ineqlin.marginals
        pm, col = v2.price_v2(y, m, pos, sink, U)
        if pm >= 1 - 1e-6:
            break
        cols.append(col)
    A = np.array(cols).T
    res = linprog(-np.ones(A.shape[1]), A_ub=A, b_ub=np.maximum(b, 1e-12), bounds=(0, None), method="highs")
    return res.x, -res.fun


def main():
    a = sys.argv[1:]
    name, sname, seed = a[0], a[1], int(a[2])
    R = int(a[a.index("--replan") + 1]) if "--replan" in a else 50
    sigma = float(a[a.index("--noise") + 1]) if "--noise" in a else 0.0
    iters = int(a[a.index("--iters") + 1]) if "--iters" in a else 200
    reiters = int(a[a.index("--reiters") + 1]) if "--reiters" in a else 20
    m = v2.Model(name)
    rng = np.random.default_rng(100 + seed)
    pos = rng.uniform(0, 100, (100, 2))
    sink = np.array(v2.SINKS[sname])
    n = len(pos)
    alive = np.ones(n, bool)
    U = v2.uplinks(m, pos, sink, alive)
    E = np.full(n, 0.5)
    cols = [U.sum(0)]
    nrng = np.random.default_rng(7 + seed)
    r = 0
    while True:
        b = E * (1 + sigma * nrng.standard_normal(n))
        x, val = plan(m, pos, sink, U, b, cols, iters if r == 0 else reiters, nrng)
        print(f"  round {r}: plan value {val:.1f}, columns {len(cols)}", file=sys.stderr, flush=True)
        E -= m.erx_ctrl * 4  # schedule broadcast: every node receives a 100-byte schedule frame per re-plan
        if val < 1:
            seq = [int(np.argmax(x))]
        else:
            w = x / x.sum() * R
            cnt = np.floor(w).astype(int)
            rem = R - cnt.sum()
            cnt[np.argsort(-(w - cnt))[:rem]] += 1
            seq = [c for c in np.flatnonzero(cnt) for _ in range(cnt[c])]
            nrng.shuffle(seq)
        for c in seq:
            E -= cols[c]
            r += 1
            if (E <= 0).any():
                print(f"LPSCHED {name} {sname} seed {seed} replan {R} noise {sigma}: FND {r}", flush=True)
                return


if __name__ == "__main__":
    main()
