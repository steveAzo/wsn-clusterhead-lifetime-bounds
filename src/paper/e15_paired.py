"""Paired comparisons across the 20 layouts of E13 (second review, point 3.3).

Every protocol ran on the same 20 layouts, so differences are paired per layout. For each setting this reports
(i) the most-often-best protocol against the runner-up (by mean FND) and (ii) DIRECT against PSO-C:
mean paired difference in rounds with a 95% t-interval, the same as a percentage of the second protocol's mean,
layouts won, the exact two-sided Wilcoxon signed-rank p, and the effect size d_z = mean(d) / sd(d).
Writes draft/tab_paired_body.tex and prints the numbers used in the text.
Usage (from Paper5/): python -I src/paper/e15_paired.py
"""
import math
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e13_tables import NAME, ORDER, P, PNAME, load13  # noqa: E402


def paired(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    sd = d.std(ddof=1)
    h = stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)
    p = stats.wilcoxon(d, zero_method="zsplit").pvalue if np.any(d != 0) else 1.0
    dz = d.mean() / sd if sd > 0 else float("inf")
    return d.mean(), d.mean() - h, d.mean() + h, 100 * d.mean() / np.mean(b), int((d > 0).sum()), int((d < 0).sum()), p, dz


def fn(x):
    return f"$-${-x:.0f}" if round(x) < 0 else f"{x:.0f}"


def fp(p):
    return "$<10^{-4}$" if p < 1e-4 else f"{p:.4f}" if p < 0.01 else f"{p:.2f}"


def fdz(x):
    return "--" if not np.isfinite(x) else f"{x:.1f}"


def main():
    d = load13("results/e13_main.txt")
    rows, prev = [], None
    for m, s in ORDER:
        L = sorted(k[2] for k in d if k[0] == m and k[1] == s)
        if not L:
            continue
        if prev and prev != m:
            rows.append("\\midrule")
        prev = m
        fnd = {p: np.array([d[(m, s, k)][p] for k in L]) for p in P}
        rank = sorted(P, key=lambda p: -fnd[p].mean())
        best, second = rank[0], rank[1]
        r1 = paired(fnd[best], fnd[second])
        r2 = paired(fnd["DIRECT"], fnd["PSOC"])
        print(f"{NAME[m]:9s} {s:6s} n={len(L)} {best}-{second}: {r1[0]:.1f} [{r1[1]:.1f},{r1[2]:.1f}] {r1[3]:+.0f}% "
              f"wins {r1[4]}/{r1[5]} p={r1[6]:.2g} dz={r1[7]:.2f} | DIRECT-PSOC: {r2[0]:.1f} [{r2[1]:.1f},{r2[2]:.1f}] "
              f"{r2[3]:+.0f}% wins {r2[4]}/{r2[5]} p={r2[6]:.2g} dz={r2[7]:.2f}")
        rows.append(
            f"{NAME[m]} & {s} & {PNAME[best]} $-$ {PNAME[second]} & {fn(r1[0])} ({fn(r1[1])} to {fn(r1[2])}) & "
            f"{r1[3]:+.0f}\\% & {r1[4]}/{len(L)} & {fp(r1[6])} & {fdz(r1[7])} & "
            f"{fn(r2[0])} ({fn(r2[1])} to {fn(r2[2])}) & {r2[4]}/{len(L)} & {fp(r2[6])} \\\\")
    open("draft/tab_paired_body.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
