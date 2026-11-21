"""Write draft/tab_audit_coding.tex (appendix table of the coded CH papers) from papers/audit/coding.csv.
Usage (from Paper5/): python -I src/paper/make_audit_table.py
"""
import csv

rows = list(csv.DictReader(open("papers/audit/coding.csv", encoding="utf-8")))
yn = {"0": "no", "1": "yes"}
model = {"FO": "first-order", "OTHER": "other", "NONE": "not stated"}
sink = {"centre": "centre/inside", "edge": "edge", "outside": "outside", "unstated": "not stated"}
out = [
    "\\begin{table}[ht]",
    "\\centering",
    "\\caption{Coded cluster-head papers (Europe PMC identifiers). DS: datasheet radio in the simulation; Bound: comparison"
    " with an optimum or bound; Idle: idle listening modelled; Direct: direct transmission as a baseline.}",
    "\\label{tab:coding}",
    "\\scriptsize",
    "\\begin{tabular}{llllllll}",
    "\\toprule",
    "Article & Year & Energy model & Sink & DS & Bound & Idle & Direct \\\\",
    "\\midrule",
]
for r in sorted(rows, key=lambda x: (x["year"], x["key"])):
    out.append(f"{r['key']} & {r['year']} & {model[r['energy_model']]} & {sink[r['sink']]} & {yn[r['datasheet_sim']]} & "
               f"{yn[r['bound_or_optimum']]} & {yn[r['idle_listening_modelled']]} & {yn[r['direct_baseline']]} \\\\")
out += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
open("draft/tab_audit_coding.tex", "w", encoding="utf-8").write("\n".join(out))
print(len(rows), "rows")
