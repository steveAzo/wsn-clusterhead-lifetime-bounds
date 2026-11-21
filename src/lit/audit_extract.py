"""E9 step 2: extract evaluation-practice fields from the audit sample PDFs (papers/audit/pdf -> audit/txt, audit/audit.csv).

Fields (regex on full text; every flag is a keyword detection to be spot-checked by hand on a random subset):
  fo_const   first-order constants present (50 nJ/bit with 10 pJ/bit/m2 or 0.0013 pJ/bit/m4, or "first order radio model")
  e_mp       0.0013 pJ/bit/m4 present; e_fs 10 pJ present; e_elec 50 nJ present
  sink_far   sink at (50,175) or (50,150) or (100,250)-style outside-field coordinates; sink_centre (50,50)/(100,100)/"centre"
  field      field size like 100 x 100 / 200 x 200; nodes like "100 nodes"
  listen     idle listening / overhearing / duty cycle mentioned
  datasheet  CC2420, CC1000, CC2538, CC1101, nRF, SX127x, TelosB, MICAz, Zolertia, ESP32 named
  testbed    real deployment / testbed / hardware experiment wording
  sim        MATLAB / NS-2 / NS-3 / OMNeT / Castalia / Python simulation
  bounds     optimal / upper bound / exact / ILP / CPLEX / Gurobi compared
  baselines  LEACH, HEED, PSO, GWO, WOA, GA, SEP, DEEC mentioned
  gain_max   largest "x% improvement/increase/longer/better" number in the text (claimed gains)
Usage (from Paper5/papers): python -I ../src/lit/audit_extract.py
"""
import csv
import glob
import json
import os
import re
import sys

import pymupdf

sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("audit/txt", exist_ok=True)
meta = {}
for line in open("audit/sample.jsonl", encoding="utf-8"):
    r = json.loads(line)
    meta[re.sub(r"[^A-Za-z0-9]", "", str(r["id"]).rsplit("/", 1)[-1])] = r


def text_of(p):
    out = "audit/txt/" + os.path.basename(p)[:-4] + ".txt"
    if os.path.exists(out):
        return open(out, encoding="utf-8").read()
    try:
        with pymupdf.open(p) as doc:
            t = "\n".join(pg.get_text() for pg in doc)
    except Exception:  # noqa: BLE001
        t = ""
    open(out, "w", encoding="utf-8").write(t)
    return t


R = {
    "e_elec": r"50\s*n\s*J\s*/?\s*bit|50\s*nJ",
    "e_fs": r"10\s*p\s*J\s*/?\s*bit\s*/?\s*m\s*\^?\s*2|10\s*pJ",
    "e_mp": r"0\.0013\s*p\s*J|0\.0013",
    "fo_words": r"first[\s-]*order\s+radio|first[\s-]*order\s+energy|radio\s+energy\s+dissipation\s+model",
    "sink_far": r"\(\s*50\s*,\s*1[5-7]\d\s*\)|\(\s*100\s*,\s*[23]\d\d\s*\)|outside\s+(the\s+)?(sensing\s+)?(field|area|region)",
    "sink_centre": r"\(\s*50\s*,\s*50\s*\)|\(\s*100\s*,\s*100\s*\)|(cent(er|re)\s+of\s+the\s+(field|area|network|region))",
    "field100": r"100\s*(m)?\s*[x×\*]\s*100",
    "listen": r"idle[\s-]*listen|overhear|duty[\s-]*cycl|listening\s+energy",
    "datasheet": r"CC2420|CC1000|CC2538|CC2650|CC1101|CC1352|nRF5|SX127|SX126|TelosB|Tmote|MICA[z2]?\b|Zolertia|ESP32|XBee|AT86RF",
    "testbed": r"test[\s-]*bed|real[\s-]*(world\s+)?(deployment|hardware|experiment)|hardware\s+(implementation|experiment)|prototype",
    "sim": r"MATLAB|NS-?2|NS-?3|OMNeT|Castalia|Cooja|Python",
    "bounds": r"upper\s+bound|optimal\s+solution\s+(obtained|computed)|ILP|integer\s+linear|CPLEX|Gurobi|exact\s+(solution|method)",
}
BASE = ["LEACH", "HEED", "SEP", "DEEC", "PSO", "GWO", "WOA", "GA\\b", "ACO", "ABC"]
GAIN = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%\s*(?:higher|more|longer|better|improvement|increase|improves|improved|extension|enhancement)", re.I)

rows = []
files = sorted(glob.glob("audit/pdf/*.pdf")) + [f for f in sorted(glob.glob("audit/txt/*.txt"))
                                                  if not os.path.exists("audit/pdf/" + os.path.basename(f)[:-4] + ".pdf")]
for p in files:
    key = os.path.basename(p)[:-4]
    t = text_of(p) if p.endswith(".pdf") else open(p, encoding="utf-8").read()
    if len(t) < 3000:
        continue
    m = meta.get(key, {})
    row = {"key": key, "year": m.get("year"), "venue": m.get("venue"), "title": (m.get("title") or "")[:120], "chars": len(t)}
    for k, rx in R.items():
        row[k] = int(bool(re.search(rx, t, re.I)))
    row["fo_const"] = int((row["e_elec"] and (row["e_fs"] or row["e_mp"])) or row["fo_words"])
    row["baselines"] = ";".join(b.replace("\\b", "") for b in BASE if re.search(r"\b" + b, t))
    g = [float(x) for x in GAIN.findall(t) if float(x) <= 1000]
    row["gain_max"] = max(g) if g else ""
    rows.append(row)
with open("audit/audit.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
n = len(rows)
print("papers with text:", n)
for k in ["fo_const", "e_mp", "fo_words", "sink_far", "sink_centre", "field100", "listen", "datasheet", "testbed", "sim", "bounds"]:
    print(f"  {k:12s} {sum(r[k] for r in rows):4d}  ({100*sum(r[k] for r in rows)/n:5.1f}%)")
print("  FO and no datasheet radio:", sum(1 for r in rows if r["fo_const"] and not r["datasheet"]))
print("  FO and no idle listening:", sum(1 for r in rows if r["fo_const"] and not r["listen"]))
print("  bounds compared:", sum(r["bounds"] for r in rows))
gm = [r["gain_max"] for r in rows if r["gain_max"] != ""]
if gm:
    print("  claimed max gain: median", sorted(gm)[len(gm) // 2], "papers with a % claim", len(gm))
