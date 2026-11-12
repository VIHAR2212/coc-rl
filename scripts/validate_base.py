"""Validate base layout JSON files in data/bases/ against grid bounds, overlaps, and TH8 limits."""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BASES_DIR = DATA_DIR / "bases"
TH_LEVEL = 8
EXPECTED_GRID = 44


def _load_defs() -> dict:
    raw = json.loads((DATA_DIR / "defenses.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _load_th8_limits() -> dict[str, int]:
    th_raw = json.loads((DATA_DIR / "raw" / "Town_Hall.json").read_text(encoding="utf-8"))
    tables = th_raw["tables"]

    th_avail = next(t for t in tables if t and t[0].get("Town Hall Level") == "Number Available")
    res_avail = next(t for t in tables if t and "Gold & Elixir Storage" in t[0])
    def_avail = next(t for t in tables if t and "Cannon" in t[0] and "Wall" in t[0])

    res_row = next(r for r in res_avail if r.get("TH Level", "").strip() == str(TH_LEVEL))
    def_row = next(r for r in def_avail if r.get("TH Level", "").strip() == str(TH_LEVEL))

    storage_each = int(res_row["Gold & Elixir Storage"])
    return {
        "town_hall": int(th_avail[0][str(TH_LEVEL)]),
        "cannon": int(def_row["Cannon"]),
        "archer_tower": int(def_row["Archer Tower"]),
        "mortar": int(def_row["Mortar"]),
        "air_defense": int(def_row["Air Defense"]),
        "wizard_tower": int(def_row["Wizard Tower"]),
        "gold_storage": storage_each,
        "elixir_storage": storage_each,
    }


def validate_base(base_path: Path, defs: dict | None = None, limits: dict[str, int] | None = None) -> list[str]:
    """Return a list of validation error messages for a base JSON (empty if valid)."""
    defs = defs or _load_defs()
    limits = limits or _load_th8_limits()
    cfg = json.loads(base_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    grid = cfg.get("grid")
    if grid != EXPECTED_GRID:
        errors.append(f"grid must be {EXPECTED_GRID}, got {grid!r}")
        return errors

    buildings = cfg.get("buildings", [])
    if not buildings:
        return ["buildings list is empty"]

    placed: list[tuple[int, str, int, int, int]] = []
    counts: Counter[str] = Counter()

    for idx, b in enumerate(buildings):
        kind = b.get("type")
        if kind not in defs:
            errors.append(f"building[{idx}]: unknown type {kind!r}")
            continue
        x, y = b.get("x"), b.get("y")
        size = int(defs[kind]["size"])
        if not (isinstance(x, int) and isinstance(y, int)):
            errors.append(f"building[{idx}] ({kind}): x, y must be integers, got ({x!r}, {y!r})")
            continue
        if x < 0 or y < 0 or x + size > grid or y + size > grid:
            errors.append(
                f"building[{idx}] ({kind} {size}x{size} at ({x}, {y})): outside 0..{grid} grid"
            )
        counts[kind] += 1
        placed.append((idx, kind, x, y, size))

    for i, (idx_a, kind_a, ax, ay, asize) in enumerate(placed):
        for idx_b, kind_b, bx, by, bsize in placed[i + 1:]:
            if ax < bx + bsize and bx < ax + asize and ay < by + bsize and by < ay + asize:
                errors.append(
                    f"overlap: building[{idx_a}] {kind_a}@({ax},{ay},{asize}x{asize}) "
                    f"and building[{idx_b}] {kind_b}@({bx},{by},{bsize}x{bsize})"
                )

    if counts["town_hall"] < 1:
        errors.append("missing town_hall")

    for kind, limit in limits.items():
        if counts[kind] > limit:
            errors.append(f"{kind}: count {counts[kind]} exceeds TH{TH_LEVEL} limit {limit}")

    combined_storage_limit = limits["gold_storage"] + limits["elixir_storage"]
    total_storages = counts["gold_storage"] + counts["elixir_storage"] + counts["storage"]
    if total_storages > combined_storage_limit:
        errors.append(f"total storages ({total_storages}) exceed TH{TH_LEVEL} limit {combined_storage_limit}")

    return errors


def main(argv: list[str] | None = None) -> int:
    paths = [Path(p) for p in argv] if argv else sorted(BASES_DIR.glob("*.json"))
    if not paths:
        print("No base JSON files found.", file=sys.stderr)
        return 1

    defs = _load_defs()
    limits = _load_th8_limits()
    failed = False
    for path in paths:
        errs = validate_base(path, defs=defs, limits=limits)
        if errs:
            failed = True
            print(f"FAIL {path.name}:")
            for e in errs:
                print(f"  - {e}")
        else:
            count = len(json.loads(path.read_text(encoding="utf-8"))["buildings"])
            print(f"OK   {path.name} ({count} buildings)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

