"""Citation spot-check for Milestone M1e:
Stratified sample of 150 rows from data/reference/clash_explorer_all.json / .csv.
Fetches cited URLs (Fandom API, coc.guide, etc.), caches them, and cross-checks HP, DPS, Level.
Generates data/reference/CITATION_CHECK.md.
"""
import json
import math
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
FANDOM_CACHE = RAW_DIR / "fandom_cache"
COCGUIDE_CACHE = RAW_DIR / "cocguide_cache"
REF_DIR = DATA_DIR / "reference"

FANDOM_CACHE.mkdir(parents=True, exist_ok=True)
COCGUIDE_CACHE.mkdir(parents=True, exist_ok=True)

HEADERS_FANDOM = {"User-Agent": "coc-rl-student-project/0.1 (educational; contact: your-email)"}
HEADERS_GENERIC = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

FANDOM_API = "https://clashofclans.fandom.com/api.php"

# Rate limiting tracker
last_request_time = 0.0

def rate_limit(interval=1.0):
    global last_request_time
    now = time.time()
    elapsed = now - last_request_time
    if elapsed < interval:
        time.sleep(interval - elapsed)
    last_request_time = time.time()


# ----------------------------------------------------------------------
# 1. Page Fetchers & Parsers with Caching
# ----------------------------------------------------------------------
def parse_fandom_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    infobox = {}
    for item in soup.select("[data-source]"):
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
        if body:
            tables.append(body)
    return {"infobox": infobox, "tables": tables, "raw_text": soup.get_text(" ", strip=True)}


def fetch_fandom_page(page_name: str) -> dict | None:
    safe_name = page_name.replace("/", "_").replace(":", "_").replace(" ", "_")
    # Check data/raw/ first
    existing_raw = RAW_DIR / f"{safe_name}.json"
    if existing_raw.exists():
        try:
            return json.loads(existing_raw.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Check fandom_cache/
    cached = FANDOM_CACHE / f"{safe_name}.json"
    if cached.exists():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Fetch from API
    rate_limit(1.0)
    try:
        r = requests.get(
            FANDOM_API,
            params={"action": "parse", "page": page_name, "prop": "text", "format": "json", "redirects": 1},
            headers=HEADERS_FANDOM,
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if "error" in data or "parse" not in data:
            return None
        html = data["parse"]["text"]["*"]
        parsed = parse_fandom_html(html)
        cached.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return parsed
    except Exception as e:
        print(f"Error fetching Fandom page {page_name}: {e}")
        return None


def fetch_cocguide_page(url: str) -> dict | None:
    slug = url.split("coc.guide/")[-1].replace("/", "_").replace("?", "_")
    cached = COCGUIDE_CACHE / f"{slug}.json"
    if cached.exists():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except Exception:
            pass

    rate_limit(1.0)
    try:
        r = requests.get(url, headers=HEADERS_GENERIC, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        tables = []
        for t in soup.find_all("table"):
            rows = []
            for tr in t.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        parsed = {"tables": tables, "raw_text": soup.get_text(" ", strip=True)}
        cached.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return parsed
    except Exception as e:
        print(f"Error fetching coc.guide page {url}: {e}")
        return None


def check_generic_url(url: str) -> str:
    rate_limit(1.0)
    try:
        r = requests.get(url, headers=HEADERS_GENERIC, timeout=10)
        if r.status_code == 200:
            return "reachable"
        return "unreachable"
    except Exception:
        return "unreachable"


# ----------------------------------------------------------------------
# 2. Value Normalization & Verification Logic
# ----------------------------------------------------------------------
def clean_num(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def verify_against_fandom(row: dict, page_data: dict) -> tuple[str, str]:
    """Check if (level, hp, dps) appear on Fandom page."""
    lvl = row.get("level")
    row_hp = row.get("hitpoints")
    row_dps = row.get("dps")

    tables = page_data.get("tables", [])
    matching_level_rows = []

    for t in tables:
        for r in t:
            for k, v in r.items():
                if k and ("level" in k.lower() or k == "") and str(v).strip() == str(lvl):
                    matching_level_rows.append(r)
                    break

    if not matching_level_rows:
        # Check if the page is just a description or general page without level tables
        return "page does not contain the value", f"Level {lvl} not found in any table on page"

    # We found rows with this level! Now check HP and DPS.
    c_row_hp = clean_num(row_hp)
    c_row_dps = clean_num(row_dps)

    hp_found = False
    dps_found = False
    page_hp_val = None
    page_dps_val = None

    for r in matching_level_rows:
        # Find HP column
        for col, val in r.items():
            if col and any(w in col.lower() for w in ["hitpoint", "hp", "health"]):
                page_hp_val = val
                c_p_hp = clean_num(val)
                if c_row_hp is not None and c_p_hp is not None:
                    if abs(c_row_hp - c_p_hp) < 1.0 or str(c_row_hp) in str(val):
                        hp_found = True
            if col and any(w in col.lower() for w in ["damage per second", "dps"]):
                page_dps_val = val
                c_p_dps = clean_num(val)
                if c_row_dps is not None and c_p_dps is not None:
                    if abs(c_row_dps - c_p_dps) < 1.0 or str(c_row_dps) in str(val):
                        dps_found = True

    # If row has no DPS (e.g. storage/wall/camp/spell), ignore DPS check
    needs_dps = c_row_dps is not None and c_row_dps > 0
    needs_hp = c_row_hp is not None and c_row_hp > 0

    if not needs_hp and not needs_dps:
        # Non-numeric equipment or special
        raw_text = page_data.get("raw_text", "")
        if str(lvl) in raw_text:
            return "match", f"Level {lvl} present"
        return "page does not contain the value", "Non-numeric stats not found"

    if needs_hp and needs_dps:
        if hp_found and dps_found:
            return "match", f"HP {row_hp} and DPS {row_dps} matched (Page: HP={page_hp_val}, DPS={page_dps_val})"
        return "mismatch", f"Expected HP={row_hp}, DPS={row_dps} | Page has HP={page_hp_val}, DPS={page_dps_val}"
    elif needs_hp:
        if hp_found:
            return "match", f"HP {row_hp} matched (Page: HP={page_hp_val})"
        return "mismatch", f"Expected HP={row_hp} | Page has HP={page_hp_val}"
    elif needs_dps:
        if dps_found:
            return "match", f"DPS {row_dps} matched (Page: DPS={page_dps_val})"
        return "mismatch", f"Expected DPS={row_dps} | Page has DPS={page_dps_val}"

    return "mismatch", "Values could not be matched"


def verify_against_cocguide(row: dict, page_data: dict) -> tuple[str, str]:
    lvl = str(row.get("level"))
    c_row_hp = clean_num(row.get("hitpoints"))
    c_row_dps = clean_num(row.get("dps"))

    tables = page_data.get("tables", [])
    matching_row = None
    for t in tables:
        for r in t:
            if r and r[0].strip() == lvl:
                matching_row = r
                break
        if matching_row:
            break

    if not matching_row:
        return "page does not contain the value", f"Level {lvl} not in coc.guide table"

    # On coc.guide:
    # Typically: [Level, DPS, Damage per hit, HP, ...]
    page_dps_val = matching_row[1] if len(matching_row) > 1 else None
    page_hp_val = matching_row[3] if len(matching_row) > 3 else None

    c_p_dps = clean_num(page_dps_val)
    c_p_hp = clean_num(page_hp_val)

    needs_dps = c_row_dps is not None and c_row_dps > 0
    needs_hp = c_row_hp is not None and c_row_hp > 0

    dps_ok = (not needs_dps) or (c_row_dps is not None and c_p_dps is not None and abs(c_row_dps - c_p_dps) < 1.0)
    hp_ok = (not needs_hp) or (c_row_hp is not None and c_p_hp is not None and abs(c_row_hp - c_p_hp) < 1.0)

    if dps_ok and hp_ok:
        return "match", f"HP and DPS matched on coc.guide (HP={page_hp_val}, DPS={page_dps_val})"
    return "mismatch", f"Expected HP={row.get('hitpoints')}, DPS={row.get('dps')} | coc.guide has HP={page_hp_val}, DPS={page_dps_val}"


# ----------------------------------------------------------------------
# 3. Stratified Sampling of 150 Rows
# ----------------------------------------------------------------------
def take_stratified_sample(rows: list[dict], target=150, seed=42) -> list[dict]:
    # Deterministic sorting
    sorted_rows = sorted(
        rows,
        key=lambda r: (
            r.get("village") or "",
            r.get("category") or "",
            str(r.get("thRequired") or ""),
            r.get("name") or "",
            r.get("level") or 0,
            r.get("id") or "",
        ),
    )
    strata = defaultdict(list)
    for r in sorted_rows:
        strata[(r.get("village"), r.get("category"), str(r.get("thRequired")))].append(r)

    N = len(sorted_rows)
    quotas = {s: len(s_rows) * target / N for s, s_rows in strata.items()}
    allocated = {s: int(math.floor(q)) for s, q in quotas.items()}
    remainder = target - sum(allocated.values())
    remainders = sorted(quotas.keys(), key=lambda s: (quotas[s] - allocated[s], s), reverse=True)
    for s in remainders[:remainder]:
        allocated[s] += 1

    rng = random.Random(seed)
    sample = []
    for s, k in allocated.items():
        if k > 0:
            sample.extend(rng.sample(strata[s], k))
    return sample


def run():
    print("Loading data/reference/clash_explorer_all.json...")
    all_rows = json.loads((REF_DIR / "clash_explorer_all.json").read_text(encoding="utf-8"))
    print(f"Total rows in dataset: {len(all_rows)}")

    sample = take_stratified_sample(all_rows, target=150, seed=42)
    print(f"Stratified sample size: {len(sample)}")

    # Category and Village breakdown of sample
    print("Sample category counts:", Counter(r["category"] for r in sample))

    results = []
    # Save sampled records and verify each citation
    print("\nStarting citation spot-check across 150 rows...")
    t0 = time.time()

    for idx, row in enumerate(sample, 1):
        name = row["name"]
        cat = row["category"]
        village = row["village"]
        lvl = row["level"]
        confidence = row.get("confidence", "UNKNOWN")
        sources = row.get("sources", [])

        row_eval = {
            "index": idx,
            "id": row.get("id"),
            "name": name,
            "category": cat,
            "village": village,
            "level": lvl,
            "thRequired": row.get("thRequired"),
            "hitpoints": row.get("hitpoints"),
            "dps": row.get("dps"),
            "confidence": confidence,
            "citations": [],
            "overall_status": "unreachable",
        }

        if not sources:
            row_eval["citations"].append({
                "url": "none",
                "site": "none",
                "status": "page does not contain the value",
                "detail": "No sources cited",
            })
            row_eval["overall_status"] = "page does not contain the value"
            results.append(row_eval)
            continue

        citation_statuses = []
        for s in sources:
            url = s.get("url") or ""
            domain = urlparse(url).netloc.lower()
            site_label = "other"
            status = "unreachable"
            detail = ""

            if "clashofclans.fandom.com" in domain:
                site_label = "fandom"
                page_name = unquote(url.split("/wiki/")[-1].split("?")[0].split("#")[0])
                page_data = fetch_fandom_page(page_name)
                if page_data is None:
                    status = "URL unreachable"
                    detail = f"Failed to fetch Fandom page: {page_name}"
                else:
                    status, detail = verify_against_fandom(row, page_data)
            elif "coc.guide" in domain:
                site_label = "coc.guide"
                page_data = fetch_cocguide_page(url)
                if page_data is None:
                    status = "URL unreachable"
                    detail = f"Failed to fetch coc.guide URL: {url}"
                else:
                    status, detail = verify_against_cocguide(row, page_data)
            else:
                site_label = domain or "other"
                reach = check_generic_url(url)
                if reach == "unreachable":
                    status = "URL unreachable"
                    detail = f"HTTP request failed for {url}"
                else:
                    status = "page does not contain the value"
                    detail = f"Generic external site ({domain}); table parsing not supported"

            row_eval["citations"].append({
                "url": url,
                "site": site_label,
                "status": status,
                "detail": detail,
            })
            citation_statuses.append(status)

        # Determine overall row status
        if "match" in citation_statuses:
            row_eval["overall_status"] = "match"
        elif "mismatch" in citation_statuses:
            row_eval["overall_status"] = "mismatch"
        elif "page does not contain the value" in citation_statuses:
            row_eval["overall_status"] = "page does not contain the value"
        else:
            row_eval["overall_status"] = "URL unreachable"

        results.append(row_eval)
        if idx % 15 == 0 or idx == len(sample):
            print(f"[{idx}/150] Processed ({time.time() - t0:.1f}s) - {name} L{lvl} -> {row_eval['overall_status']}")

    # Save results to json for detailed reporting
    (REF_DIR / "citation_spot_check_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nCompleted check of 150 rows in {time.time() - t0:.1f}s")
    return results


if __name__ == "__main__":
    run()

