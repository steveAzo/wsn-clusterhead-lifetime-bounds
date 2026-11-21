"""Shares of the UB for E12 (best-k PSO-C, best-k GWO, MMAX), best E8 protocol, and the E10 LP schedule (exact reports).
Seeds 0-1 (the E12 layouts). Usage (from Paper5/): python -I src/paper/e12_table.py
"""
import re
from collections import defaultdict

ub, best4 = {}, {}
for l in open("results/e8_v2.txt", encoding="utf-8"):
    m = re.match(r"V2 (\S+) (\S+) seed (\d) rmax \S+: DIRECT=(\d+) LEACH=(\d+) KMRE=(\d+) PSOC=(\d+) LP=\[([\d.]+),([\d.]+)\]", l)
    if m:
        k = (m[1], m[2], int(m[3]))
        ub[k] = float(m[9])
        best4[k] = max(int(m[i]) for i in range(4, 8))
lp = {}
for l in open("results/e10_lp_protocol.txt", encoding="utf-8"):
    m = re.match(r"LPSCHED (\S+) (\S+) seed (\d) replan 50 noise 0.0: FND (\d+)", l)
    if m:
        lp[(m[1], m[2], int(m[3]))] = int(m[4])
rows = defaultdict(lambda: defaultdict(list))
for l in open("results/e12_baselines.txt", encoding="utf-8"):
    m = re.match(r"M12 (\S+) (\S+) seed (\d): (.*)", l)
    if not m:
        continue
    k = (m[1], m[2], int(m[3]))
    v = dict(x.split("=") for x in m[4].split())
    v = {a: int(b) for a, b in v.items()}
    if k not in ub:
        print("no UB yet", k)
        continue
    U = ub[k]
    pso = max(v[f"PSOC_k{j}"] for j in (3, 5, 8))
    gwo = max(v[f"GWO_k{j}"] for j in (3, 5, 8))
    kp = max((3, 5, 8), key=lambda j: v[f"PSOC_k{j}"])
    kg = max((3, 5, 8), key=lambda j: v[f"GWO_k{j}"])
    r = rows[(m[1], m[2])]
    r["pso"].append(pso / U); r["gwo"].append(gwo / U); r["mmax"].append(v["MMAX"] / U)
    r["best4"].append(best4[k] / U); r["kp"].append(kp); r["kg"].append(kg)
    r["psok5"].append(v["PSOC_k5"] / U)
    if k in lp:
        r["lp"].append(lp[k] / U)
    print(k, f"PSO {pso}(k{kp}) GWO {gwo}(k{kg}) MMAX {v['MMAX']} best4 {best4[k]} LP {lp.get(k)} UB {U:.0f}")
mean = lambda x: sum(x) / len(x) if x else float("nan")
print()
for k, r in rows.items():
    print(k, " ".join(f"{a}={mean(b):.2f}" for a, b in r.items() if a not in ("kp", "kg")), "kp", r["kp"], "kg", r["kg"],
          "n", len(r["pso"]), "nlp", len(r["lp"]))
