# Base Layouts (M2)

> **Note:** These layouts are **hand-made approximations**, not real player bases from Clash of Clans.

## Layouts
- `base01.json` — Starter minimal sample base (9 buildings).
- `base02.json` — TH8 compact core (27 buildings + 108 Level 8 walls).
- `base03.json` — TH8 spread-out layout (27 buildings, open/unwalled).
- `base04.json` — TH8 defenses-outside layout (27 buildings + 176 Level 8 walls in core and outer rings).
- `base05.json` — TH8 defenses-clustered layout (27 buildings, open/unwalled).
- `base06.json` — TH8 mixed asymmetric layout (27 buildings + 130 Level 8 walls).
- `base07.json` — TH8 Southern Teaser layout (27 buildings + 92 Level 8 walls, held-out eval only).
- `base08.json` — TH8 Ring / Moated Core layout (27 buildings + 144 Level 8 walls, held-out eval only).
- `base09.json` — TH8 Four-Quadrant Island layout (27 buildings + 88 Level 8 walls, held-out eval only).
- `base10.json` — TH8 Wide Anti-Splash Bastion layout (27 buildings + 42 Level 8 walls, held-out eval only).

## Notes & Deferred Mechanics
- **Walls (M4):** `base02.json`, `base04.json`, and `base06.json`–`base10.json` include 1x1 Level 8 walls within the TH8 wiki limit of 225 (`data/raw/Town_Hall.json` & `data/raw/Wall.json`). Walls are excluded from destruction %.
- **TH8 building limits:** Layouts `base02.json`–`base10.json` use only building types defined in `data/defenses.json` up to the TH8 maximum counts from `data/raw/Town_Hall.json` (1 Town Hall, 5 Cannons, 5 Archer Towers, 4 Mortars, 3 Air Defenses, 3 Wizard Towers, 3 Gold Storages, 3 Elixir Storages, up to 225 Walls).
- Validate all layouts with `python scripts/validate_base.py`.

