"""nRF52840 with the unscaled version 2.0 currents (E14b, results/e14b_nrf_v2.txt) against the main runs with the version 3.0
currents (results/e13_main.txt), layouts 0-2: best protocol per layout, best/UB, best (FND-1)/ILB, PSO-C against DIRECT, and
the smallest ILB/UB. Also counts, for the edge sink, the nodes whose minimum-energy route to the sink uses a relay.
Usage (from Paper5/): python -I src/paper/e15_nrf_v2.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scoping"))
from e13_tables import P, load13  # noqa: E402
import e8_model_v2 as v2  # noqa: E402

a, b = load13("results/e14b_nrf_v2.txt"), load13("results/e13_main.txt")
for s in ("far", "edge", "centre"):
    for tag, d, m in (("v2.0", a, "nRF52840"), ("v3.0", b, "nRF52840v3")):
        ks = [(m, s, i) for i in range(3)]
        best = [max(d[k][p] for p in P) / d[k]["UB"] for k in ks]
        win = [max(P, key=lambda p: d[k][p]) for k in ks]
        bi = [(max(d[k][p] for p in P) - 1) / d[k]["ILB"] for k in ks]
        gain = [d[k]["PSOC"] / d[k]["DIRECT"] - 1 for k in ks]
        print(f"{s:6s} {tag}: best/UB {np.round(best, 2)} mean {np.mean(best):.2f}, best {win}, best/ILB {np.mean(bi):.2f}, "
              f"PSO-C/DIRECT-1 {np.round(gain, 2)}, min ILB/UB {min(d[k]['ILB'] / d[k]['UB'] for k in ks):.3f}")
for name in ("nRF52840", "nRF52840v3"):
    m = v2.Model(name)
    for seed in range(3):
        pos = np.random.default_rng(100 + seed).uniform(0, 100, (100, 2))
        U = v2.uplinks(m, pos, np.array(v2.SINKS["edge"]), np.ones(100, bool))
        relayed = int(((U - np.diag(np.diag(U))) > 0).any(1).sum())
        print(f"{name} edge layout {seed}: nodes routed through a relay {relayed}, "
              f"largest per-round load {1e3 * U.sum(0).max():.3f} mJ")
