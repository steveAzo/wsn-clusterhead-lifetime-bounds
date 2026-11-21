"""E11 summary: best protocol share of the UB, and per-protocol shares, by radio, sink, and reporting interval Tr.
Also the same with no sleep baseline (E8 v2, same layouts). Usage (from Paper5/): python -I src/paper/e11_table.py
"""
import re
from collections import defaultdict

P = ["DIRECT", "LEACH", "KMRE", "PSOC"]
pat = re.compile(r"(?:L11|V2) (\S+) (\S+) seed (\d)(?: Tr (\d+))?.*?DIRECT=(\d+) LEACH=(\d+) KMRE=(\d+) PSOC=(\d+) LP=\[([\d.]+),([\d.]+)\]")


def load(path, tr_default=None):
    out = {}
    for l in open(path, encoding="utf-8"):
        m = pat.match(l)
        if m:
            tr = m[4] or tr_default
            out[(m[1], m[2], int(m[3]), tr)] = ([int(m[i]) for i in range(5, 9)], float(m[9]), float(m[10]))
    return out


e11 = load("results/e11_listening.txt")
e8 = load("results/e8_v2.txt", "none")
agg = defaultdict(lambda: defaultdict(list))
for (m, s, seed, tr), (v, lb, ub) in e11.items():
    a = agg[(m, s, tr)]
    a["best"].append(max(v) / ub); a["bestname"].append(P[v.index(max(v))])
    for p, x in zip(P, v):
        a[p].append(x / ub)
    a["lbub"].append(lb / ub); a["ub"].append(ub)
    if (m, s, seed, "none") in e8:
        v0, lb0, ub0 = e8[(m, s, seed, "none")]
        b = agg[(m, s, "none")]
        if seed not in b["seeds"]:
            b["seeds"].append(seed); b["best"].append(max(v0) / ub0); b["bestname"].append(P[v0.index(max(v0))])
            for p, x in zip(P, v0):
                b[p].append(x / ub0)
            b["ub"].append(ub0)
mean = lambda x: sum(x) / len(x)
for k in sorted(agg, key=lambda k: (k[0], k[1], {"none": 0, "300": 1, "60": 2, "10": 3}[k[2]])):
    a = agg[k]
    print(f"{k[0]:11s} {k[1]:6s} Tr={k[2]:4s} n={len(a['best'])} best={mean(a['best']):.2f} ({','.join(sorted(set(a['bestname'])))}) "
          + " ".join(f"{p}={mean(a[p]):.2f}" for p in P) + f" UB={mean(a['ub']):.0f}"
          + (f" LB/UB min={min(a['lbub']):.3f}" if a["lbub"] else ""))
