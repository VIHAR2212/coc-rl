# Base Layouts (M2)

> **Note:** These layouts are **hand-made approximations**, not real player bases from Clash of Clans.

## Layouts
- `base01.json` — Starter minimal sample base (9 buildings).
- `base02.json` — TH8 compact core (27 buildings packed around a centered Town Hall).
- `base03.json` — TH8 spread-out layout (27 buildings spaced across the 44x44 grid).
- `base04.json` — TH8 defenses-outside layout (Town Hall + storages inside, 20 defenses forming an outer ring).
- `base05.json` — TH8 defenses-clustered layout (20 defenses grouped around the Town Hall on the west, storages offset east).
- `base06.json` — TH8 mixed asymmetric layout (offset Town Hall, triangular Air Defenses/Mortars, storages tanking flanks).

## Notes & Deferred Mechanics
- **Walls skipped (pending M4):** `sim/env.py` does not model walls or pathfinding yet, so walls are intentionally omitted from `base02.json`–`base06.json` and will be added in milestone **M4**.
- **TH8 building limits:** Layouts `base02.json`–`base06.json` use only building types defined in `data/defenses.json` up to the TH8 maximum counts from `data/raw/Town_Hall.json` (1 Town Hall, 5 Cannons, 5 Archer Towers, 4 Mortars, 3 Air Defenses, 3 Wizard Towers, 3 Gold Storages, 3 Elixir Storages).
- Validate all layouts with `python scripts/validate_base.py`.

