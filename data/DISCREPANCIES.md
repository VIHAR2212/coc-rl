# Data Discrepancies & Missing Stats (TH8, M1)

Cross-check of Town Hall 8 (Laboratory level 6) stats between the **Clash of Clans Fandom wiki** (`data/raw/*.json`, fetched 2026-11-12) and **coc.guide** (fetched 2026-11-12).

## Troop HP & DPS Cross-Check (Lab Level 6)

| Troop | Level | Fandom HP | coc.guide HP | Fandom DPS | coc.guide DPS | `stats_verified` | Notes |
|---|---:|---:|---:|---:|---:|:---:|---|
| Giant | 5 | 900 | 800 | 31 | 31 | `false` | **HP mismatch** (900 vs 800). `coc.guide` lags behind balance updates (e.g., Giant stops at level 13 there). |
| Barbarian | 5 | 105 | 105 | 23 | 23 | `true` | Exact match on HP and DPS. |
| Archer | 5 | 40 | 40 | 20 | 20 | `true` | Exact match on HP and DPS. |
| Wall Breaker | 5 | 53 | 53 | 43 (base dmg, 1s atk) | 43 (dmg/hit) | `true` | HP and base hit damage agree; `coc.guide` omits a separate DPS column (one-shot suicide unit) and lists Range `0.5 Tiles` vs Fandom `1 tile`. |
| Goblin | 5 | 65 | 65 | 32 (64 vs resources) | 32 | `true` | Exact match on HP and base DPS. |

## Building / Defense Cross-Check (TH8 Max Levels)

| Building | TH8 Max Level | Fandom HP | coc.guide HP | Fandom DPS | coc.guide DPS | `stats_verified` |
|---|---:|---:|---:|---:|---:|:---:|
| Cannon | 10 | 960 | 960 | 64 | 64 | `true` |
| Archer Tower | 10 | 810 | 810 | 63 | 63 | `true` |
| Mortar | 6 | 650 | 650 | 11 | 11 | `true` |
| Air Defense | 6 | 1050 | 1050 | 230 | 230 | `true` |
| Wizard Tower | 6 | 960 | 960 | 32 | 32 | `true` |
| Town Hall | 8 | 3900 | 3900 | 0 | 0 | `true` |
| Gold Storage | 11 | 2100 | 2100 | 0 | 0 | `true` |
| Elixir Storage | 11 | 2100 | 2100 | 0 | 0 | `true` |

## Missing / Unverified Stats & Simplifications

- **Movement speed (`speed_verified: false`):** `coc.guide` does not list troop movement speeds. Fandom wiki reports unitless speeds (`Giant: 12`, `Barbarian: 18`, `Archer: 24`, `Wall Breaker: 24`, `Goblin: 32`). `scripts/normalize.py` retains `speed_raw` and converts via `speed_tiles_per_s = speed_raw * 0.125` (`SPEED_TO_TILES_PER_S = 0.125`), which remains **unverified** until calibrated against a real attack recording.
- **Wall Breaker splash radius & range difference:** Fandom lists `Range: 1 tile` and `Damage Radius: 2 tiles`, whereas `coc.guide` lists `Range: 0.5 Tiles` (Super Wall Breaker summary table).
- **Projectile travel delay / projectile speed (missing):** Neither the Fandom wiki tables (`data/raw/*.json`) nor `coc.guide` provide projectile flight speed or impact delay in seconds. In M5 (`sim/env.py`), `Building.projectile_delay` reads `projectile_delay` from `data/defenses.json` (defaulting to `0.0` with a `# TODO` until calibrated or supplied) while discrete shot cadence uses `attack_speed` and `damage = dps * attack_speed` from `data/defenses.json`.
- **Wall Breaker & Goblin stats:** Wall Breaker one-shot wall detonation (`damage_vs_walls: 1720`, `splash_radius: 2.0`) is modeled in M4; Goblin `dps_vs_resources` (`64`) is stored in `data/troops.json` (currently using `dps: 32` uniformly until resource-multiplier mechanic is explicitly requested).
- **TH8 flying troops (skipped in M5):** `data/raw/` and `data/troops.json` contain only the 5 scraped ground troops (`Barbarian`, `Archer`, `Giant`, `Wall Breaker`, `Goblin`). `Troop.is_flying` and `Air Defense` (`targets: "air"`) targeting are implemented and unit-tested, while adding playable flying troops (e.g., Balloon / Dragon / Minion) is skipped because their wiki pages were not scraped in M1.

