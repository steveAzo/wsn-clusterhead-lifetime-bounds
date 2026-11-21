"""E10: the LP schedule as a protocol (v2 energy model), versus PSO-C and the exact bound.

LPSCHED: every R rounds the sink solves the role-assignment LP (column generation, exact v2 pricing, capped iterations)
with b = reported residual energies (true energy x (1 + noise), noise ~ N(0, sigma) per node and report), turns the LP
solution x_c into an integer sequence for the next R rounds (largest-remainder apportionment over x_c / sum x), and
executes it with true energies. Control cost of the schedule broadcast is in the v2 per-round control term.
Output: FND rounds. Compare with results/e8_v2.txt (PSOC, LP bracket) for the same case.
Usage: python -I src/scoping/e10_lp_protocol.py <model> <sink> <seed> [--replan 50] [--noise 0.0] [--iters 200] [--reiters 20] (first plan uses --iters pricing steps, later re-plans --reiters on the pooled columns)
Revision options (E13b; defaults reproduce E10):
  --report-cost  every node sends a 200-bit energy report to the sink along its minimum-energy path at each re-plan
                 (relays pay reception and transmission), charged as CTRL_BITS/K_BITS of its data uplink
  --delay        a report describes the energy at the PREVIOUS re-plan; the sink dead-reckons it forward by subtracting
                 the charges of the rounds it scheduled since then
  --miss p       each report is lost with probability p; the sink keeps its dead-reckoned estimate for that node
"""
import os
import sys
import time

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
    rep_cost = "--report-cost" in a
    delay = "--delay" in a
    pmiss = float(a[a.index("--miss") + 1]) if "--miss" in a else 0.0
    tag = (" report-cost" if rep_cost else "") + (" delay" if delay else "") + (f" miss {pmiss}" if pmiss else "")
    rep = v2.CTRL_BITS / v2.e1.K_BITS * U.sum(0)  # energy per node of every node sending one 200-bit report
    est = E.copy()  # sink's estimate of residual energy
    E_prev = E.copy()  # true energy at the previous re-plan (what a delayed report describes)
    used_last = np.zeros(n)  # charges the sink scheduled in the last period
    r = 0
    while True:
        if rep_cost or delay or pmiss:
            if rep_cost:
                E -= rep
            got = nrng.random(n) >= pmiss
            src = (E_prev - used_last) if delay else E  # delayed report, dead-reckoned to now by the sink
            noisy = src * (1 + sigma * nrng.standard_normal(n)) if not delay else                 E_prev * (1 + sigma * nrng.standard_normal(n)) - used_last
            est = np.where(got, noisy, est - used_last)
            if rep_cost:
                est = est - rep  # the sink knows the report cost
            b = est
            E_prev = E.copy()
        else:
            b = E * (1 + sigma * nrng.standard_normal(n))
        tp = time.time()
        x, val = plan(m, pos, sink, U, b, cols, iters if r == 0 else reiters, nrng)
        print(f"  round {r}: plan value {val:.1f}, columns {len(cols)}, plan time {time.time() - tp:.1f}s", file=sys.stderr, flush=True)
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
        used_last = np.full(n, m.erx_ctrl * 4)  # the sink knows the broadcast cost
        if (E <= 0).any():  # depleted by the report itself
            print(f"LPSCHED {name} {sname} seed {seed} replan {R} noise {sigma}{tag}: FND {r}", flush=True)
            return
        for c in seq:
            E -= cols[c]
            used_last += cols[c]
            r += 1
            if (E <= 0).any():
                print(f"LPSCHED {name} {sname} seed {seed} replan {R} noise {sigma}{tag}: FND {r}", flush=True)
                return


if __name__ == "__main__":
    main()
