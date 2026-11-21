"""E9 step 3: compact excerpts for manual coding of a random sample (keyword flags for testbed/bounds/sink proved unreliable).

For each sampled paper prints: title, venue, year; sentences with energy-model constants; sentences locating the
base station/sink; field size and node count; simulator; hardware names; sentences with optimal/optimum/exact/bound;
sentences with idle listening/duty cycle. The coder fills papers/audit/coding.csv (one row per paper).
Usage (from Paper5/papers): python -I ../src/lit/audit_excerpts.py <n> <seed> [start]  > audit/excerpts_<seed>.txt
"""
import json
import random
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
n, seed = int(sys.argv[1]), int(sys.argv[2])
start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
meta = {json.loads(line)["id"]: json.loads(line) for line in open("audit/sample.jsonl", encoding="utf-8")}
import glob  # noqa: E402
import os  # noqa: E402
keys = sorted(os.path.basename(f)[:-4] for f in glob.glob("audit/txt/PMC*.txt"))
random.Random(seed).shuffle(keys)
PAT = {
    "ENERGY": r"(50\s*n\s*J|E\s*_?\s*elec|first[\s-]*order|0\.0013|10\s*p\s*J|\bmA\b|\bmW\b|datasheet|energy (consumption )?model)",
    "SINK": r"((base station|sink|\bBS\b)[^.]{0,80}(located|position|placed|deployed|coordinat|at \(|centre|center|outside|corner|edge))|\(\s*\d{2,3}\s*,\s*\d{2,3}\s*\)",
    "FIELD": r"\d{2,4}\s*(m)?\s*[x×\*]\s*\d{2,4}\s*m|\b\d{2,4}\s+(sensor\s+)?nodes\b",
    "SIM": r"MATLAB|NS-?2|NS-?3|OMNeT|Castalia|Cooja|Python|simulat(ed|ion) (in|using|with)",
    "HW": r"CC2420|CC1000|CC2538|CC2650|CC1101|nRF5|SX12|TelosB|Tmote|MICA|Zolertia|ESP32|XBee|Arduino|Raspberry|LoRa\b",
    "OPT": r"(optimal|optimum|exact|upper bound|lower bound|CPLEX|Gurobi|MILP|ILP)[^.]{0,80}(compar|solution|lifetime|benchmark|gap)",
    "LISTEN": r"idle[\s-]*listen|overhear|duty[\s-]*cycl|sleep (mode|state)",
}
for k in keys[start:start + n]:
    t = open(f"audit/txt/{k}.txt", encoding="utf-8").read()
    m = meta.get(k, {})
    print("=" * 100)
    print(k, "|", m.get("year"), "|", m.get("venue"), "|", (m.get("title") or "")[:150])
    sents = re.split(r"(?<=[.;])\s+", t)
    for lab, rx in PAT.items():
        hits = [s.strip()[:230] for s in sents if re.search(rx, s, re.I)]
        if lab == "ENERGY":
            hits = [h for h in hits if re.search(r"50\s*n\s*J|0\.0013|10\s*p\s*J|\bmA\b|\bmW\b|first[\s-]*order|datasheet", h, re.I)] or hits[:2]
        for h in hits[:3]:
            print(f"  [{lab}] {h}")
