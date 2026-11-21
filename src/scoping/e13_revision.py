"""E13 (revision): more layouts, an integer lower bound, and model sensitivity (v2 energy model).

For one (radio, sink, layout) this runs DIRECT, LEACH, KMRE, PSO-C (k = 5) as in E8, then column generation as in
e8_model_v2.lp_bound, and finally the restricted master as an INTEGER programme over the generated columns (HiGHS MILP).
The integer optimum over the generated columns is a whole-round schedule that can be played in any order, so
  ILB <= T_int* <= floor(UB),
where T_int* is the largest number of whole rounds that can be completed before any node is depleted. (Within the FND
window no node has died, so the alive set, the routes, and the per-round charges a_c are fixed and order does not
matter.) Protocol FND counts the round in which the first node is depleted, so FND - 1 <= T_int*.

Usage: python -I src/scoping/e13_revision.py <model> <sink> <seed> [--n 100] [--adv one|perch] [--iters 800]
                                              [--ilp-time 300] [--no-sim]
Output: R13 <model> <sink> seed <s> n <n> adv <mode>: DIRECT= LEACH= KMRE= PSOC= LB= UB= ILB= ILBgap= t=
"""
import os
import sys
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e8_model_v2 as v2  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def lp_bound_cols(m, pos, sink, iters=800, tol=0.02, warm=300, seed=0):
    """Same procedure as v2.lp_bound, but also returns the generated columns."""
    n, E0 = len(pos), 0.5
    U = v2.uplinks(m, pos, sink, np.ones(n, bool))
    if not np.isfinite(U).all():
        return None, None, None
    cols = [v2.charges(m, pos, sink, np.ones(n, bool), [], U)]
    wr = np.random.default_rng(seed)
    for k in (2, 3, 5, 8, 12, 20):
        k = min(k, n)
        cent = pos[wr.choice(n, k, replace=False)]
        for _ in range(30):
            lab = np.linalg.norm(pos[:, None] - cent[None], axis=2).argmin(1)
            cent = np.array([pos[lab == j].mean(0) if (lab == j).any() else cent[j] for j in range(k)])
        for _ in range(warm // 6):
            chs = [int(wr.choice(np.flatnonzero(lab == j))) for j in range(k) if (lab == j).any()]
            cols.append(v2.charges(m, pos, sink, np.ones(n, bool), chs, U))
    pm1, _ = v2.price_v2(np.ones(n), m, pos, sink, U)
    ub = n * E0 / pm1
    yb, alpha = None, 0.7
    lb = 0.0
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
        if ub / lb - 1 < tol:
            break
        cols.append(col)
    return lb, ub, cols


def integer_lb(cols, E0, time_limit):
    """Largest whole-round schedule over the generated columns: max 1'x s.t. A x <= E0 (strict margin), x integer >= 0.
    A tiny margin keeps every node strictly above zero, so all nodes are alive after the schedule."""
    A = np.array(cols).T
    n, K = A.shape
    res = milp(-np.ones(K), constraints=LinearConstraint(A, -np.inf, np.full(n, E0 * (1 - 1e-9))),
               integrality=np.ones(K), bounds=Bounds(0, np.inf),
               options={"time_limit": time_limit, "mip_rel_gap": 1e-4})
    if res.x is None:
        return None
    x = np.floor(res.x + 1e-6)
    while (A @ x > E0 * (1 - 1e-9)).any():  # guard against solver tolerance: drop rounds until feasible
        x[np.argmax(x)] -= 1
    # greedy fill: add whole rounds while every node stays strictly positive
    left = E0 - A @ x
    while True:
        ok = np.flatnonzero((A <= left[:, None] - 1e-12).all(0))
        if len(ok) == 0:
            break
        c = ok[np.argmin((A[:, ok] / np.maximum(left[:, None], 1e-15)).max(0))]
        x[c] += 1
        left -= A[:, c]
    return int(x.sum())


def main():
    a = sys.argv[1:]
    name, sname, seed = a[0], a[1], int(a[2])
    n = int(a[a.index("--n") + 1]) if "--n" in a else 100
    v2.ADV_MODE = a[a.index("--adv") + 1] if "--adv" in a else "one"
    iters = int(a[a.index("--iters") + 1]) if "--iters" in a else 800
    tl = float(a[a.index("--ilp-time") + 1]) if "--ilp-time" in a else 300
    m = v2.Model(name)
    rng = np.random.default_rng(100 + seed)
    pos = rng.uniform(0, 100, (n, 2))
    sink = np.array(v2.SINKS[sname])
    out = {}
    t0 = time.time()
    if "--no-sim" not in a:
        for s in ("DIRECT", "LEACH", "KMRE", "PSOC"):
            out[s] = v2.simulate(s, m, pos, sink, 5, np.random.default_rng(11 + seed))
    lb, ub, cols = lp_bound_cols(m, pos, sink, iters=iters, seed=seed)
    if lb is None:
        out["LP"] = "unreachable"
    else:
        ilb = integer_lb(cols, 0.5, tl)
        out["LB"] = f"{lb:.1f}"
        out["UB"] = f"{ub:.1f}"
        out["ILB"] = ilb
        out["ncols"] = len(cols)
    out["pricing"] = f"{v2.PRICE_CALLS[0]}/{v2.PRICE_CALLS[1]}nonopt"
    out["t"] = f"{time.time() - t0:.0f}s"
    print(f"R13 {name} {sname} seed {seed} n {n} adv {v2.ADV_MODE}: " + " ".join(f"{k}={v}" for k, v in out.items()),
          flush=True)


if __name__ == "__main__":
    main()
