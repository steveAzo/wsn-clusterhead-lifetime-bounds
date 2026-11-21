"""Revision tables from E13 (20 layouts, integer lower bound), E13 advert/density variants, E13b LP schedule variants,
and E12 with layout 2. Writes LaTeX bodies to draft/tab_*.tex and prints the numbers used in the text.
Usage (from Paper5/): python -I src/paper/e13_tables.py
"""
import math
import re
from collections import defaultdict

import numpy as np
from scipy import stats

P = ["DIRECT", "LEACH", "KMRE", "PSOC"]
NAME = {"FO": "FO", "CC2420": "CC2420", "nRF52840v3": "nRF52840", "CC1101-868": "CC1101"}
PNAME = {"DIRECT": "DIRECT", "LEACH": "LEACH", "KMRE": "KMRE", "PSOC": "PSO-C"}
ORDER = [(m, s) for m in ["FO", "CC2420", "nRF52840v3", "CC1101-868"] for s in ["far", "edge", "centre"]]


def load13(path, n=100, adv="one"):
    d = {}
    import os
    if not os.path.exists(path):
        return d
    for l in open(path, encoding="utf-8"):
        m = re.match(r"R13 (\S+) (\S+) seed (\d+) n (\d+) adv (\S+): (.*)", l)
        if not m or int(m[4]) != n or m[5] != adv:
            continue
        v = dict(x.split("=", 1) for x in m[6].split())
        if "UB" not in v:
            continue
        rec = {p: int(v[p]) for p in P if p in v}
        rec.update(LB=float(v["LB"]), UB=float(v["UB"]), ILB=int(v["ILB"]) if v["ILB"] != "None" else None,
                   pricing=v.get("pricing", ""))
        d[(m[1], m[2], int(m[3]))] = rec
    return d


def ci(x):
    x = np.asarray(x, float)
    if len(x) < 2:
        return float("nan"), float("nan")
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))
    return x.mean() - h, x.mean() + h


def f2(x):
    return f"{x:.2f}"


def main():
    d = load13("results/e13_main.txt")
    seeds = sorted({k[2] for k in d})
    full = [s for s in seeds if all((m, sk, s) in d for m, sk in ORDER if not (m == "CC2420" and sk == "far"))]
    print("layouts complete in every setting:", len(full), full)
    L = full
    # ---- tab:gap (means) and tab:var (variability of best/UB) ----
    gap, var, txt = [], [], {}
    nonopt = 0
    ilb_ub_all, lb_ub_all, ilb_lb_all = [], [], []
    for i, (m, s) in enumerate(ORDER):
        if i and ORDER[i - 1][0] != m:
            gap.append("\\midrule"); var.append("\\midrule")
        if m == "CC2420" and s == "far":
            gap.append(f"CC2420 & far & \\multicolumn{{8}}{{l}}{{infeasible: sink beyond the range of every node}} \\\\")
            continue
        R = [d[(m, s, x)] for x in L]
        if not R:
            continue
        mean = {p: np.mean([r[p] for r in R]) for p in P}
        lb, ub = np.mean([r["LB"] for r in R]), np.mean([r["UB"] for r in R])
        ilb = np.mean([r["ILB"] for r in R])
        iu = [r["ILB"] / r["UB"] for r in R]
        ilb_ub_all += iu; lb_ub_all += [r["LB"] / r["UB"] for r in R]
        ilb_lb_all += [r["ILB"] / r["LB"] for r in R]
        nonopt += sum(int(re.search(r"/(\d+)nonopt", r["pricing"])[1]) for r in R if "nonopt" in r["pricing"])
        best = [max(r[p] for p in P) / r["UB"] for r in R]
        winners = [max(P, key=lambda p: r[p]) for r in R]
        wc = {p: winners.count(p) for p in P}
        top = max(wc, key=wc.get)
        q1, med, q3 = np.percentile(best, [25, 50, 75])
        lo, hi = ci(best)
        pso = [r["PSOC"] / r["UB"] for r in R]
        gap.append(f"{NAME[m]} & {s} & " + " & ".join(f"{mean[p]:.0f}" for p in P) +
                   f" & {ilb:.0f} & {lb:.0f} & {ub:.0f} & {min(iu):.3f} \\\\")
        var.append(f"{NAME[m]} & {s} & {np.mean(best):.2f} & {np.std(best, ddof=1):.3f} & {lo:.2f}--{hi:.2f} & "
                   f"{med:.2f} ({q1:.2f}--{q3:.2f}) & {min(best):.2f}--{max(best):.2f} & {PNAME[top]} ({wc[top]}/{len(R)}) "
                   f"& {np.mean(pso):.2f} \\\\")
        txt[(m, s)] = dict(best=np.mean(best), bmin=min(best), bmax=max(best), top=top, wc=wc[top], n=len(R),
                           pso=np.mean(pso), mean=mean, ilb=ilb, ub=ub)
    open("draft/tab_gap_body.tex", "w", encoding="utf-8").write("\n".join(gap) + "\n")
    open("draft/tab_var_body.tex", "w", encoding="utf-8").write("\n".join(var) + "\n")
    print(f"N={len(L)}  ILB/UB min {min(ilb_ub_all):.4f} median {np.median(ilb_ub_all):.4f}; "
          f"LB/UB min {min(lb_ub_all):.4f}; ILB/LB min {min(ilb_lb_all):.4f}; pricing calls not optimal: {nonopt}")
    for k, v in txt.items():
        print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items() if a != "mean"},
              {p: round(x) for p, x in v["mean"].items()})
    # ---- advert sensitivity (layouts 0-2) ----
    da = load13("results/e13_adv.txt", adv="perch")
    rows = []
    for m, s in ORDER:
        ks = [(m, s, x) for x in range(3) if (m, s, x) in da and (m, s, x) in d]
        if not ks:
            continue
        b1 = [max(d[k][p] for p in P) / d[k]["UB"] for k in ks]
        b2 = [max(da[k][p] for p in P) / da[k]["UB"] for k in ks]
        w1 = max(P, key=lambda p: np.mean([d[k][p] for k in ks]))
        w2 = max(P, key=lambda p: np.mean([da[k][p] for k in ks]))
        u1, u2 = np.mean([d[k]["UB"] for k in ks]), np.mean([da[k]["UB"] for k in ks])
        rows.append(f"{NAME[m]} & {s} & {u1:.0f} & {u2:.0f} & {np.mean(b1):.2f} ({PNAME[w1]}) & "
                    f"{np.mean(b2):.2f} ({PNAME[w2]}) & {min(da[k]['ILB'] / da[k]['UB'] for k in ks):.3f} \\\\")
        print("ADV", m, s, len(ks), rows[-1])
    open("draft/tab_adv_body.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
    # ---- density ----
    rows = []
    for nn in (50, 100, 200):
        dn = d if nn == 100 else load13("results/e13_density.txt", n=nn)
        for m, s in [("FO", "centre"), ("CC2420", "centre"), ("nRF52840v3", "edge")]:
            ks = [(m, s, x) for x in range(2) if (m, s, x) in dn]
            if not ks:
                continue
            b = [max(dn[k][p] for p in P) / dn[k]["UB"] for k in ks]
            w = max(P, key=lambda p: np.mean([dn[k][p] for k in ks]))
            ps = np.mean([dn[k]["PSOC"] / dn[k]["UB"] for k in ks])
            rows.append(f"{nn} & {NAME[m]} & {s} & {np.mean([dn[k]['UB'] for k in ks]):.0f} & {np.mean(b):.2f} ({PNAME[w]}) & "
                        f"{ps:.2f} & {min(dn[k]['ILB'] / dn[k]['UB'] for k in ks):.3f} \\\\")
            print("DENS", rows[-1])
    open("draft/tab_density_body.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
    # ---- LP schedule variants (layout 0) ----
    e10 = {}
    for path in ("results/e10_lp_protocol.txt", "results/e13_lpsched.txt"):
        for l in (open(path, encoding="utf-8") if __import__("os").path.exists(path) else []):
            mm = re.match(r"LPSCHED (\S+) (\S+) seed (\d) replan 50 noise (\S+)(.*): FND (\d+)", l)
            if mm:
                e10[(mm[1], mm[2], int(mm[3]), mm[4], mm[5].strip())] = int(mm[6])
    rows = []
    for m, s in [("FO", "centre"), ("CC2420", "centre"), ("nRF52840v3", "edge"), ("nRF52840v3", "centre")]:
        k = (m, s, 0)
        if k not in d:
            continue
        ub = d[k]["UB"]
        best = max(d[k][p] for p in P)
        vals = [e10.get((m, s, 0, "0.0", "")), e10.get((m, s, 0, "0.1", "")), e10.get((m, s, 0, "0.0", "report-cost")),
                e10.get((m, s, 0, "0.1", "report-cost delay miss 0.2"))]
        cells = " & ".join("--" if v is None else f"{v / ub:.2f}" for v in vals)
        rows.append(f"{NAME[m]} & {s} & {cells} & {best / ub:.2f} \\\\")
        print("LPV", m, s, vals, round(best), round(ub, 1))
    open("draft/tab_lpvar_body.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
    # ---- integer bracket for the E10 schedules (layouts 0-2): FND-1 is a feasible whole-round schedule ----
    worst = []
    for (m, s, x, nz, tag), v in e10.items():
        if nz == "0.0" and tag == "" and (m, s, x) in d:
            worst.append(((v - 1) / d[(m, s, x)]["UB"], m, s, x, v, d[(m, s, x)]["ILB"]))
    if worst:
        worst.sort()
        print("LP schedule (FND-1)/UB min", worst[0], "max", worst[-1])


if __name__ == "__main__":
    main()
