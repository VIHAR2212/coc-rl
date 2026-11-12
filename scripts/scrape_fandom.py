"""Pull stats from the Clash of Clans Fandom wiki (MediaWiki API). UNTESTED here (my sandbox can't reach Fandom): run locally, fix selectors if needed.

Usage:  python scripts/scrape_fandom.py Giant Barbarian Archer Cannon "Archer Tower"
Output: data/raw/<page>.json  = {"infobox": {...}, "tables": [[{col: value}, ...], ...]}
Raw files are CACHED; normalise them into data/troops.json / data/defenses.json in a separate step.

Etiquette: 1 request per second, descriptive User-Agent. Fandom text is CC BY-SA: keep attribution in data/SOURCES.md.
"""
import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API = "https://clashofclans.fandom.com/api.php"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
HEADERS = {"User-Agent": "coc-rl-student-project/0.1 (educational; contact: your-email)"}


def fetch_html(page):
    r = requests.get(API, params={"action": "parse", "page": page, "prop": "text", "format": "json", "redirects": 1},
                     headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"{page}: {data['error']}")
    return data["parse"]["text"]["*"]


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    infobox = {}
    for item in soup.select("[data-source]"):            # portable infobox rows
        label = item.get("data-source")
        val = item.select_one(".pi-data-value") or item
        infobox[label] = val.get_text(" ", strip=True)
    tables = []
    for t in soup.select("table"):
        rows = t.find_all("tr")
        if len(rows) < 2:
            continue
        head = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])]
        body = []
        for r in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in r.find_all(["td", "th"])]
            if cells:
                body.append(dict(zip(head, cells)))
        tables.append(body)
    return {"infobox": infobox, "tables": tables}


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for page in sys.argv[1:]:
        out = RAW / (page.replace(" ", "_") + ".json")
        if out.exists():
            print("cached:", out.name)
            continue
        out.write_text(json.dumps(parse(fetch_html(page)), indent=2, ensure_ascii=False))
        print("saved:", out.name)
        time.sleep(1)
