"""Table tab:baselines from E12 (PSO-C and GWO at k = 3, 5, 8; MMAX) and E10 (bound schedule, exact reports), as shares
of the E13 UB of the same layout (layouts 0-2), so the table uses the same bounds as tab:gap. Writes
draft/tab_baselines_body.tex. Usage (from Paper5/): python -I src/paper/e15_baselines.py
"""
import os
import re
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e13_tables import NAME, P, load13  # noqa: E402

d = load13("results/e13_main.txt")
lp = {}
for l in open("results/e10_lp_protocol.txt", encoding="utf-8"):
    m = re.match(r"LPSCHED (\S+) (\S+) seed (\d+) replan 50 noise 0.0: FND (\d+)", l)
    if m:
        lp[(m[1], m[2], int(m[3]))] = int(m[4])
r = defaultdict(lambda: defaultdict(list))
for l in open("results/e12_baselines.txt", encoding="utf-8"):
    m = re.match(r"M12 (\S+) (\S+) seed (\d+): (.*)", l)
    if not m:
        continue
    k = (m[1], m[2], int(m[3]))
    v = {a: int(b) for a, b in (x.split("=") for x in m[4].split())}
    U = d[k]["UB"]
    q = r[(m[1], m[2])]
    q["best4"].append(max(d[k][p] for p in P) / U)
    q["k5"].append(v["PSOC_k5"] / U)  # same E12 run as the tuned values
    for alg in ("PSOC", "GWO"):
        kb = max((3, 5, 8), key=lambda j: v[f"{alg}_k{j}"])
        q[alg].append(v[f"{alg}_k{kb}"] / U)
        q[alg + "k"].append(kb)
    q["MMAX"].append(v["MMAX"] / U)
    q["lp"].append(lp[k] / U)
rows, prev = [], None
for m in ["FO", "CC2420", "nRF52840v3"]:
    for s in ["far", "edge", "centre"]:
        if (m, s) not in r:
            continue
        if prev and prev != m:
            rows.append(r"\midrule")
        prev = m
        q = r[(m, s)]
        f = lambda x: f"{np.mean(q[x]):.2f}"  # noqa: E731
        kk = lambda x: "/".join(sorted({str(j) for j in q[x + "k"]}))  # noqa: E731
        print(m, s, {a: round(float(np.mean(b)), 3) for a, b in q.items() if not a.endswith("k")}, kk("PSOC"), kk("GWO"), len(q["lp"]))
        rows.append(f"{NAME[m]} & {s} & {f('best4')} & {f('k5')} & {f('PSOC')} ({kk('PSOC')}) & {f('GWO')} ({kk('GWO')}) & "
                    f"{f('MMAX')} & {f('lp')} \\\\")
open("draft/tab_baselines_body.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
