"""E10 summary (tab:lpsched) and refreshed tab:gap / tab:baselines rows. Usage (from Paper5/): python -I src/paper/e10_table.py"""
import re
from collections import defaultdict

P = ["DIRECT", "LEACH", "KMRE", "PSOC"]
e8 = {}
for l in open("results/e8_v2.txt", encoding="utf-8"):
    m = re.match(r"V2 (\S+) (\S+) seed (\d) rmax \S+: DIRECT=(\d+) LEACH=(\d+) KMRE=(\d+) PSOC=(\d+) LP=\[([\d.]+),([\d.]+)\]", l)
    if m:
        e8[(m[1], m[2], int(m[3]))] = ([int(m[i]) for i in range(4, 8)], float(m[8]), float(m[9]))
lp = {}
for l in open("results/e10_lp_protocol.txt", encoding="utf-8"):
    m = re.match(r"LPSCHED (\S+) (\S+) seed (\d) replan 50 noise (\S+): FND (\d+)", l)
    if m:
        lp[(m[1], m[2], int(m[3]), m[4])] = int(m[5])
mean = lambda x: sum(x) / len(x)
print("tab:lpsched  (shares of LB; PSO-C and best-of-four shares of LB; gain = exact LP / best protocol - 1)")
allx, alln = [], []
for s in ["centre", "edge", "far"]:
    for m in ["CC2420", "nRF52840v3", "FO"]:
        ex, nz, ps, bp, gain, raw = [], [], [], [], [], []
        for seed in range(3):
            k = (m, s, seed)
            if k not in e8 or (m, s, seed, "0.0") not in lp:
                continue
            v, lb, ub = e8[k]
            e, n = lp[(m, s, seed, "0.0")], lp[(m, s, seed, "0.1")]
            ex.append(e / lb); nz.append(n / lb); ps.append(v[3] / lb); bp.append(max(v) / lb); gain.append(e / max(v) - 1)
            raw.append((e, n, round(lb, 1)))
        if ex:
            allx += ex; alln += nz
            print(f"{m:11s} {s:6s} exact {mean(ex):.2f} ({min(ex):.2f}-{max(ex):.2f})  noise {mean(nz):.2f} ({min(nz):.2f}-{max(nz):.2f})"
                  f"  PSOC {mean(ps):.2f}  best4 {mean(bp):.2f}  gain {mean(gain)*100:.0f}% ({min(gain)*100:.0f}-{max(gain)*100:.0f})  {raw}")
print(f"ALL exact {min(allx):.3f}-{max(allx):.3f}  noise {min(alln):.3f}-{max(alln):.3f}")
print()
print("tab:gap rows (mean of three layouts)")
for (m, s) in [("FO", "far"), ("nRF52840v3", "far")]:
    rows = [e8[(m, s, i)] for i in range(3) if (m, s, i) in e8]
    v = [mean([r[0][j] for r in rows]) for j in range(4)]
    lbm, ubm = mean([r[1] for r in rows]), mean([r[2] for r in rows])
    sh = [max(r[0]) / r[2] for r in rows]
    print(m, s, len(rows), [round(x) for x in v], round(lbm), round(ubm), f"best/UB {mean(sh):.2f} ({min(sh):.2f}-{max(sh):.2f})",
          "lb/ub min", round(min(r[1] / r[2] for r in rows), 3))
print()
print("LP schedule share of UB, layouts 0-1 (tab:baselines)")
for (m, s) in [("FO", "far"), ("nRF52840v3", "far"), ("FO", "centre"), ("CC2420", "centre"), ("nRF52840v3", "edge"),
               ("FO", "edge"), ("CC2420", "edge"), ("nRF52840v3", "centre")]:
    x = [lp[(m, s, i, "0.0")] / e8[(m, s, i)][2] for i in range(2)]
    b4 = [max(e8[(m, s, i)][0]) / e8[(m, s, i)][2] for i in range(2)]
    print(m, s, f"LP {mean(x):.2f}  best4 {mean(b4):.2f}")
