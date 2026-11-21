"""Summarise results/e8_v2.txt: per radio x sink, mean lifetime per protocol, best protocol, share of the LP UB and LB."""
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
rx = re.compile(r"^V2 (\S+) (\S+) seed (\d) rmax \S+: DIRECT=(\d+) LEACH=(\d+) KMRE=(\d+) PSOC=(\d+) LP=(\S+)")
g = defaultdict(list)
for line in open("results/e8_v2.txt", encoding="utf-8"):
    m = rx.match(line)
    if m:
        g[(m[1], m[2])].append(m)
print(f"{'radio':12s} {'sink':6s} n  DIRECT  LEACH   KMRE   PSOC  best   best/UB (min-max)  PSOC/UB  LB/UB")
for (r, s), ms in g.items():
    if ms[0][8] == "unreachable":
        print(f"{r:12s} {s:6s} {len(ms)}  infeasible: sink out of range of every node")
        continue
    v = {p: [int(m[i]) for m in ms] for p, i in zip(["DIRECT", "LEACH", "KMRE", "PSOC"], range(4, 8))}
    lb = [float(m[8].strip("[]").split(",")[0]) for m in ms]
    ub = [float(m[8].strip("[]").split(",")[1]) for m in ms]
    best = [max(v[p][k] for p in v) for k in range(len(ms))]
    bp = max(v, key=lambda p: sum(v[p]))
    sh = [b / u for b, u in zip(best, ub)]
    ps = sum(p / u for p, u in zip(v["PSOC"], ub)) / len(ms)
    gap = sum(l / u for l, u in zip(lb, ub)) / len(ms)
    print(f"{r:12s} {s:6s} {len(ms)} " + " ".join(f"{sum(v[p])/len(ms):6.0f}" for p in v)
          + f"  {bp:6s} {sum(sh)/len(sh):.3f} ({min(sh):.2f}-{max(sh):.2f})    {ps:.3f}   {gap:.3f}")
