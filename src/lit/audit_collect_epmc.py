"""E9 step 1 (Europe PMC route; OpenAlex was unavailable on 2026-11-19).

Sample frame: Europe PMC open-access articles, 2021-2026, matching "cluster head" AND "wireless sensor" (full-text search).
For each: metadata to papers/audit/sample.jsonl, full text (fullTextXML stripped to plain text) to papers/audit/txt/<PMCID>.txt.
Bias to state: journals indexed in PMC (Sensors, Scientific Reports, PLoS ONE, Heliyon, ...); Elsevier/IEEE subscription
venues are absent unless open access.
Usage (from Paper5/papers): python -I ../src/lit/audit_collect_epmc.py
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "research-scoping-script"}
Q = '"cluster head" AND "wireless sensor" AND PUB_YEAR:[2021 TO 2026] AND OPEN_ACCESS:y AND SRC:MED'
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/"


def get(url, timeout=90):
    for a in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception:  # noqa: BLE001
            if a == 3:
                raise
            time.sleep(10 * (a + 1))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs("audit/txt", exist_ok=True)
    rows, cursor = [], "*"
    while True:
        u = BASE + "search?" + urllib.parse.urlencode({"query": Q, "format": "json", "pageSize": 1000, "cursorMark": cursor,
                                                       "resultType": "lite"})
        d = json.loads(get(u))
        res = d["resultList"]["result"]
        rows += [r for r in res if r.get("pmcid")]
        nxt = d.get("nextCursorMark")
        if not res or not nxt or nxt == cursor:
            break
        cursor = nxt
    print("hits with PMCID:", len(rows), flush=True)
    with open("audit/sample.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({"id": r["pmcid"], "title": r.get("title"), "year": int(r.get("pubYear") or 0),
                                 "venue": r.get("journalTitle"), "doi": r.get("doi"), "cites": r.get("citedByCount")}) + "\n")
    n = 0
    for r in rows:
        out = f"audit/txt/{r['pmcid']}.txt"
        if os.path.exists(out):
            n += 1
            continue
        try:
            x = get(BASE + f"{r['pmcid']}/fullTextXML").decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        body = re.sub(r"<ref-list.*?</ref-list>", " ", x, flags=re.S)  # drop references so cited constants do not count
        t = re.sub(r"<[^>]+>", " ", body)
        t = re.sub(r"\s+", " ", t)
        if len(t) > 3000:
            open(out, "w", encoding="utf-8").write(t)
            n += 1
        if n % 50 == 0:
            print("texts", n, flush=True)
        time.sleep(0.3)
    print("full texts saved:", n)


if __name__ == "__main__":
    main()
