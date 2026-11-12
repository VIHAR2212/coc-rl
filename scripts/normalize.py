"""Normalize cached Fandom wiki JSON files in data/raw/ into data/troops.json and data/defenses.json for TH8."""

import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TH_LEVEL = 8
FANDOM_BASE = "https://clashofclans.fandom.com/wiki/"

# Unverified conversion constant from Fandom wiki speed units to tiles/second.
# Standard community rule of thumb: speed_tiles_per_s = speed_raw * 0.125 (1/8).
# Flagged speed_verified=False until calibrated against a real attack recording.
SPEED_TO_TILES_PER_S = 0.125

# Cross-check status of HP/DPS against https://coc.guide (see data/DISCREPANCIES.md).
# Giant L5 HP differs (Fandom 900 vs coc.guide 800), so stats_verified is False.
TROOP_STATS_VERIFIED = {
    "Barbarian": True,
    "Archer": True,
    "Giant": False,
    "Wall_Breaker": True,
    "Goblin": True,
}
BUILDING_STATS_VERIFIED = {
    "Cannon": True,
    "Archer_Tower": True,
    "Mortar": True,
    "Air_Defense": True,
    "Wizard_Tower": True,
    "Town_Hall": True,
    "Gold_Storage": True,
    "Elixir_Storage": True,
}


def _load_raw(stem: str) -> dict:
    return json.loads((RAW_DIR / f"{stem}.json").read_text(encoding="utf-8"))


def _to_int(val: str) -> int:
    cleaned = val.replace(",", "").strip()
    if cleaned in ("N/A", "-", ""):
        return 0
    return int(cleaned)


def _to_float(val: str) -> float:
    m = re.search(r"[-+]?\d*\.?\d+", val.replace(",", ""))
    if not m:
        raise ValueError(f"Cannot parse float from {val!r}")
    return float(m.group(0))


def _find_table(tables: list[list[dict]], required_cols: tuple[str, ...], take_last: bool = False) -> list[dict]:
    matches = [t for t in tables if t and all(col in t[0] for col in required_cols)]
    if not matches:
        raise ValueError(f"Missing table with columns {required_cols}")
    return matches[-1] if take_last else matches[0]


def _parse_targets(text: str) -> str:
    norm = text.replace("\xa0", " ").lower()
    has_ground = "ground" in norm
    has_air = "air" in norm
    if has_ground and has_air:
        return "air_ground"
    if has_air:
        return "air"
    if has_ground:
        return "ground"
    return "none"


def _parse_favorite(text: str) -> str:
    low = text.lower()
    if "defense" in low:
        return "defenses"
    if "wall" in low:
        return "walls"
    if "resource" in low:
        return "resources"
    return "any"


def _th8_lab_level(th_raw: dict) -> int:
    table = _find_table(th_raw["tables"], ("TH Level", "Laboratory", "Barracks"), take_last=True)
    for row in table:
        if row.get("TH Level", "").strip() == str(TH_LEVEL):
            return _to_int(row["Laboratory"])
    raise ValueError(f"TH{TH_LEVEL} row not found in Town Hall Laboratory table")


def _th8_max_building_levels(th_raw: dict) -> dict[str, int]:
    def_table = _find_table(th_raw["tables"], ("TH Level", "Cannon", "Wall **"), take_last=True)
    res_table = _find_table(th_raw["tables"], ("TH Level", "Gold & Elixir Storage", "Clan Castle"), take_last=True)
    def_row = next(r for r in def_table if r.get("TH Level", "").strip() == str(TH_LEVEL))
    res_row = next(r for r in res_table if r.get("TH Level", "").strip() == str(TH_LEVEL))
    return {
        "Cannon": _to_int(def_row["Cannon"]),
        "Archer_Tower": _to_int(def_row["Archer Tower"]),
        "Mortar": _to_int(def_row["Mortar"]),
        "Air_Defense": _to_int(def_row["Air Defense"]),
        "Wizard_Tower": _to_int(def_row["Wizard Tower"]),
        "Gold_Storage": _to_int(res_row["Gold & Elixir Storage"]),
        "Elixir_Storage": _to_int(res_row["Gold & Elixir Storage"]),
        "Town_Hall": TH_LEVEL,
    }


def _normalize_troop(stem: str, lab_level: int) -> tuple[str, dict]:
    raw = _load_raw(stem)
    summary = _find_table(raw["tables"], ("Preferred Target", "Movement Speed", "Housing Space"))[0]
    levels = _find_table(raw["tables"], ("Level", "Hitpoints", "Laboratory Level Required"))
    eligible = [r for r in levels if _to_int(r["Laboratory Level Required"]) <= lab_level]
    row = max(eligible, key=lambda r: _to_int(r["Level"]))
    level = _to_int(row["Level"])
    speed_raw = _to_int(summary["Movement Speed"])
    dps = _to_float(row["Damage per Second"]) if "Damage per Second" in row else _to_float(row["Damage"])

    entry = {
        "name": stem.replace("_", " "),
        "level": level,
        "hp": _to_int(row["Hitpoints"]),
        "dps": int(dps) if dps.is_integer() else dps,
        "attack_speed": _to_float(summary["Attack Speed"]),
        "range_tiles": _to_float(summary["Range"]),
        "housing": _to_int(summary["Housing Space"]),
        "targets": _parse_targets(summary["Attack Type"]),
        "favorite": _parse_favorite(summary["Preferred Target"]),
        "speed_raw": speed_raw,
        "speed_tiles_per_s": round(speed_raw * SPEED_TO_TILES_PER_S, 4),
        "speed_verified": False,
        "stats_verified": TROOP_STATS_VERIFIED[stem],
        "source": f"{FANDOM_BASE}{stem}",
    }
    if "Damage vs. Walls" in row:
        entry["damage_vs_walls"] = _to_int(row["Damage vs. Walls"])
        entry["_note"] = "Wall Breaker deals one-shot splash damage (x40 vs Walls); dps stores base hit damage."
    if "DPS on Resource Buildings" in row:
        entry["dps_vs_resources"] = _to_int(row["DPS on Resource Buildings"])
    if stem == "Giant":
        entry["_note"] = "HP mismatch vs coc.guide (900 vs 800); see data/DISCREPANCIES.md."
    return f"{stem.lower()}_l{level}", entry


def _parse_range(range_str: str) -> tuple[float, float | None]:
    parts = [float(p) for p in re.findall(r"\d+(?:\.\d+)?", range_str)]
    if len(parts) == 2:
        return parts[1], parts[0]
    return parts[0], None


def _normalize_building(stem: str, expected_level: int) -> tuple[str, dict]:
    raw = _load_raw(stem)
    size = _to_int(_find_table(raw["tables"], ("Size",))[0]["Size"].split("x")[0])
    if stem == "Town_Hall":
        th_table = _find_table(raw["tables"], ("TH Level", "Hitpoints", "Build Cost"))
        row = next(r for r in th_table if r.get("TH Level", "").strip() == str(TH_LEVEL))
        return "town_hall", {
            "level": TH_LEVEL,
            "hp": _to_int(row["Hitpoints"]),
            "dps": 0,
            "attack_speed": 0.0,
            "range_tiles": 0.0,
            "size": size,
            "targets": "none",
            "stats_verified": BUILDING_STATS_VERIFIED[stem],
            "source": f"{FANDOM_BASE}{stem}",
        }

    levels = _find_table(raw["tables"], ("Level", "Hitpoints", "Town Hall Level Required"))
    eligible = [
        r for r in levels
        if r["Town Hall Level Required"].strip().isdigit() and int(r["Town Hall Level Required"]) <= TH_LEVEL
    ]
    row = max(eligible, key=lambda r: _to_int(r["Level"]))
    level = _to_int(row["Level"])
    if level != expected_level:
        raise ValueError(f"{stem}: table level {level} != Town Hall table level {expected_level}")

    entry = {
        "level": level,
        "hp": _to_int(row["Hitpoints"]),
        "dps": _to_int(row["Damage per Second"]) if "Damage per Second" in row else 0,
        "attack_speed": 0.0,
        "range_tiles": 0.0,
        "size": size,
        "targets": "none",
        "stats_verified": BUILDING_STATS_VERIFIED[stem],
        "source": f"{FANDOM_BASE}{stem}",
    }
    if "Damage per Second" in row:
        combat = _find_table(raw["tables"], ("Range", "Attack Speed", "Unit Type Targeted"))[0]
        max_r, min_r = _parse_range(combat["Range"])
        entry["attack_speed"] = _to_float(combat["Attack Speed"])
        entry["range_tiles"] = max_r
        if min_r is not None:
            entry["min_range_tiles"] = min_r
        entry["targets"] = _parse_targets(combat["Unit Type Targeted"])
        splash = re.search(r"(\d+(?:\.\d+)?)\s*tile", combat.get("Damage Type", ""))
        if splash:
            entry["splash_radius"] = float(splash.group(1))
    return stem.lower(), entry


def main() -> None:
    th_raw = _load_raw("Town_Hall")
    lab_level = _th8_lab_level(th_raw)
    building_levels = _th8_max_building_levels(th_raw)

    troops = {
        "_note": (
            f"TH{TH_LEVEL} troop stats (Laboratory level {lab_level}) normalized from Clash of Clans Fandom wiki "
            f"(data/raw/) and cross-checked against coc.guide. "
            f"speed_tiles_per_s = speed_raw * {SPEED_TO_TILES_PER_S} (unverified until calibrated)."
        )
    }
    for stem in ("Giant", "Barbarian", "Archer", "Wall_Breaker", "Goblin"):
        key, val = _normalize_troop(stem, lab_level)
        troops[key] = val

    defenses = {
        "_note": (
            f"TH{TH_LEVEL} building/defense stats normalized from Clash of Clans Fandom wiki (data/raw/) "
            "and cross-checked against coc.guide."
        )
    }
    for stem in ("Cannon", "Archer_Tower", "Mortar", "Air_Defense", "Wizard_Tower", "Town_Hall", "Gold_Storage", "Elixir_Storage"):
        key, val = _normalize_building(stem, building_levels[stem])
        defenses[key] = val

    # Keep 'storage' alias for starter data/bases/base01.json until M2 updates base layouts.
    defenses["storage"] = {
        **defenses["gold_storage"],
        "_note": "Alias for gold_storage/elixir_storage used by starter base01.json.",
    }

    (DATA_DIR / "troops.json").write_text(json.dumps(troops, indent=2) + "\n", encoding="utf-8")
    (DATA_DIR / "defenses.json").write_text(json.dumps(defenses, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote troops.json ({len(troops) - 1} troops) and defenses.json ({len(defenses) - 1} buildings) for TH{TH_LEVEL} (Lab {lab_level}).")


if __name__ == "__main__":
    main()
