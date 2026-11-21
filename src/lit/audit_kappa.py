"""Agreement between coder 1 (papers/audit/coding.csv + sample80.csv) and coder 2 (papers/audit/second_coder/coder2.csv).
Usage (from Paper5): python -I src/lit/audit_kappa.py"""
import csv
from collections import Counter

c1 = {r["key"]: r for r in csv.DictReader(open("papers/audit/coding.csv", encoding="utf-8"))}
inc = {r["pmcid"]: r["included"] for r in csv.DictReader(open("papers/audit/sample80.csv", encoding="utf-8"))}
c2 = list(csv.DictReader(open("papers/audit/second_coder/coder2.csv", encoding="utf-8")))
key2 = {h.split("(")[0]: h for h in c2[0].keys()}


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n**2
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


norm = lambda v: {"unstated": "none", "": "none"}.get((v or "").strip().lower(), (v or "").strip().lower())  # noqa: E731
a = [inc[r["pmcid"]] for r in c2]
b = [r[key2["ch_protocol"]].strip() for r in c2]
po, k = kappa(a, b)
print(f"ch_protocol (screening): n={len(a)} agreement={po:.2f} kappa={k:.2f}")
both = [r for r in c2 if inc[r["pmcid"]] == "1" and r[key2["ch_protocol"]].strip() == "1"]
for item in ["energy_model", "sink", "datasheet_sim", "bound_or_optimum", "idle_listening_modelled", "direct_baseline"]:
    a = [norm(c1[r["pmcid"]][item]) for r in both]
    b = [norm(r[key2[item]]) for r in both]
    if a:
        po, k = kappa(a, b)
        print(f"{item}: n={len(a)} agreement={po:.2f} kappa={k:.2f}")
