"""E9 step 1: collect a sample of recent (2021-2026) open-access WSN cluster-head / clustering-routing papers for the
evaluation-practice audit. OpenAlex search; keeps works with an open PDF URL; downloads into papers/audit/pdf (only files
starting with %PDF). Writes papers/audit/sample.jsonl (metadata for every candidate, downloaded or not).
Usage (from Paper5/papers): python -I ../src/lit/audit_collect.py [--per-query 60] [--max 220]
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research scoping script)"}
QUERIES = [
    "cluster head selection wireless sensor network optimization algorithm",
    "energy efficient clustering routing protocol wireless sensor network metaheuristic",
    "particle swarm optimization clustering wireless sensor network lifetime",
    "grey wolf optimizer cluster head wireless sensor network",
    "whale optimization clustering wireless sensor network",
    "genetic algorithm cluster head selection wireless sensor network energy",
    "LEACH improved cluster head selection energy network lifetime",
]


def get(url, timeout=60):
    for a in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:  # noqa: BLE001
            if ("429" in str(e) or "503" in str(e)) and a < 4:
                time.sleep(20 * (a + 1))
                continue
            raise


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    per = int(args[args.index("--per-query") + 1]) if "--per-query" in args else 60
    mx = int(args[args.index("--max") + 1]) if "--max" in args else 220
    os.makedirs("audit/pdf", exist_ok=True)
    seen, rows = set(), []
    for q in QUERIES:
        params = {"search": q, "per-page": per, "filter": "from_publication_date:2021-01-01,open_access.is_oa:true,type:article",
                  "sort": "relevance_score:desc"}
        try:
            r = json.loads(get("https://api.openalex.org/works?" + urllib.parse.urlencode(params)))
        except Exception as e:  # noqa: BLE001
            print("ERR", q, e, flush=True)
            continue
        for w in r["results"]:
            if w["id"] in seen:
                continue
            seen.add(w["id"])
            src = ((w.get("primary_location") or {}).get("source") or {})
            pdf = (w.get("best_oa_location") or {}).get("pdf_url")
            rows.append({"id": w["id"], "title": w["display_name"], "year": w["publication_year"], "venue": src.get("display_name"),
                         "issn": src.get("issn_l"), "doi": w.get("doi"), "cites": w["cited_by_count"], "pdf": pdf, "q": q})
        print(q, "->", len(rows), flush=True)
        time.sleep(2)
    with open("audit/sample.jsonl", "w", encoding="utf-8") as fh:
        for x in rows:
            fh.write(json.dumps(x) + "\n")
    n = 0
    for x in rows:
        if n >= mx or not x["pdf"]:
            continue
        key = re.sub(r"[^A-Za-z0-9]", "", x["id"].rsplit("/", 1)[-1])
        path = f"audit/pdf/{key}.pdf"
        if os.path.exists(path):
            n += 1
            continue
        try:
            data = get(x["pdf"], 60)
        except Exception:  # noqa: BLE001
            continue
        if data[:5] == b"%PDF-" and len(data) < 15_000_000:
            open(path, "wb").write(data)
            n += 1
            print("ok", n, key, (x["title"] or "")[:70], flush=True)
        time.sleep(1)
    print("downloaded", n, "of", sum(1 for x in rows if x["pdf"]), "with open PDF;", len(rows), "candidates")


if __name__ == "__main__":
    main()
