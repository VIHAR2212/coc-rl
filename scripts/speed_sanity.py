"""Sanity-check troop movement speeds in data/troops.json (time to cross 20 tiles)."""

import json
from pathlib import Path

TROOPS_PATH = Path(__file__).resolve().parent.parent / "data" / "troops.json"
DISTANCE_TILES = 20.0


def main():
    raw = json.loads(TROOPS_PATH.read_text(encoding="utf-8"))
    troops = {k: v for k, v in raw.items() if not k.startswith("_")}

    print(f"{'Troop':<16} {'Raw':>5} {'tiles/s':>9} {'20-tile time':>14} {'Verified':>10}  Flag")
    print("-" * 78)
    for k, t in troops.items():
        spd = t["speed_tiles_per_s"]
        time_20 = DISTANCE_TILES / spd
        # Sanity bounds: <1.0 or >6.0 tiles/s for ground TH8 elixir troops is suspicious.
        flag = "OK (uncalibrated constant 0.125)"
        if spd < 1.0 or spd > 6.0:
            flag = "IMPLAUSIBLE speed"
        print(
            f"{t['name']:<16} {t['speed_raw']:>5} {spd:>9.2f} {time_20:>13.2f}s "
            f"{str(t['speed_verified']):>10}  {flag}"
        )


if __name__ == "__main__":
    main()

