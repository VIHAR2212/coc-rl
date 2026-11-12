"""Turn the stat tables on coc.guide troop/defense pages into JSON.  UNTESTED: run locally and fix the parsing if the site layout differs.

Usage:  python scripts/scrape_cocguide.py troop giant
        python scripts/scrape_cocguide.py defense cannon   (check the real slug from the site's index page first)
Prints each table as a list of {header: value} rows. Copy the level you need into data/*.json.
"""
import json
import sys

import requests
from bs4 import BeautifulSoup


def scrape(section, slug):
    url = f"https://coc.guide/{section}/{slug}"
    html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (student project)"}).text
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if not rows:
            continue
        head = [c.get_text(" ", strip=True) or (c.find("img") or {}).get("alt", "") for c in rows[0].find_all(["th", "td"])]
        data = []
        for r in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in r.find_all(["td", "th"])]
            data.append(dict(zip(head, cells)))
        tables.append(data)
    return {"url": url, "tables": tables}


if __name__ == "__main__":
    print(json.dumps(scrape(sys.argv[1], sys.argv[2]), indent=2))
