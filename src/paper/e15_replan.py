"""Table tab:replan from E14 (re-plan interval R of the bound schedule, layout 0), with R = 50 from E10/E13b/E14.
FND and FND as a share of the E13 UB, exact reports and realistic reports (report cost, one re-plan old, 20% lost,
10% noise). Writes draft/tab_replan_body.tex. Usage (from Paper5/): python -I src/paper/e15_replan.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e13_tables import load13  # noqa: E402

d = load13("results/e13_main.txt")
fnd = {}
for path in ("results/e10_lp_protocol.txt", "results/e13_lpsched.txt", "results/e14_replan.txt"):
    for l in open(path, encoding="utf-8"):
        m = re.match(r"LPSCHED (\S+) (\S+) seed 0 replan (\d+) noise (\S+)(.*?): FND (\d+)", l)
        if m:
            kind = "exact" if (m[4], m[5].strip()) == ("0.0", "") else \
                "real" if (m[4], m[5].strip()) == ("0.1", "report-cost delay miss 0.2") else None
            if kind:
                fnd[(m[1], m[2], int(m[3]), kind)] = int(m[6])
rows = []
for R in (10, 25, 50, 100, 200):
    cells = []
    for m, s in (("FO", "centre"), ("CC2420", "edge")):
        ub = d[(m, s, 0)]["UB"]
        for kind in ("exact", "real"):
            v = fnd.get((m, s, R, kind))
            cells.append("--" if v is None else f"{v} ({v / ub:.2f})")
    rows.append(f"{R} & " + " & ".join(cells) + " \\\\")
    print(rows[-1])
for m, s in (("FO", "centre"), ("CC2420", "edge")):
    print(m, s, "UB", d[(m, s, 0)]["UB"], "best4", max(d[(m, s, 0)][p] for p in ("DIRECT", "LEACH", "KMRE", "PSOC")))
open("draft/tab_replan_body.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
