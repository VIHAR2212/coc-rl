# Progress Log

## STEP 0 (Precondition)
- **Status:** PASSED (`data/armies.json` exists; M2b `evaluate.py` > 0% on all 6 bases).

## Milestone M3 (RENDER)
- **Status:** PASSED (Attempt 2, commit `7a42d2c`)
- **Needs human check:** Visual inspection of `docs/baseline_attack.gif`, PNG frames in `docs/`, and `play_human.py`.

## Milestone M4 (WALLS AND PATHING)
- **Status:** PASSED (Attempt 3)
- **Passed:**
  - (a) 1x1 `wall` (L8: 3000 HP, max 225 from Fandom `Wall.json` + `Town_Hall.json`, cross-checked on `coc.guide`) excluded from destruction %.
  - (b) 8-way A* pathing in `sim/pathing.py`, wall-attack fallback when blocked, Wall Breaker targeting & 1720 wall splash detonation in `sim/env.py`.
  - (c) `pytest -q`: `10 passed in 5.87s` (3 tests in `tests/test_walls_pathing.py`); `check_env OK`.
  - (d) Added Level 8 walls to `base02.json` (108), `base04.json` (176), `base06.json` (130); `validate_base.py` passed all 6 bases.
  - (e) `evaluate.py` ran end-to-end (`base01` 100% `giant_barch`, `base03` 70.4%, `base04` 55.6%, `base06` 29.6%, `base05` 11.1%, `base02` 0.0%); benchmarked `243.9 steps/s`.

## Milestone M5 (DEFENSE REALISM)
- **Status:** PASSED (Attempt 1)
- **Passed:**
  - (a) Mortar (`min_range_tiles=4.0`, `splash_radius=1.5`), Wizard Tower (`splash_radius=1.0`), Air Defense (`targets="air"` air-only), `attack_speed` discrete shots (`dps * attack_speed`), and `PendingProjectile` delay queue in `sim/entities.py` and `sim/env.py`. Missing `projectile_delay` wiki stat flagged in `data/DISCREPANCIES.md` and `# TODO` in `sim/env.py` (defaults to `0.0`).
  - (b) `tests/test_defenses_m5.py`: 5 unit tests (one per mechanic) pass; `pytest -q` -> `15 passed in 11.04s`; `check_env OK`.
  - (c) Flying troops skipped (`data/raw/` and `data/troops.json` only have the 5 M1 ground troops; `Troop.is_flying` + Air Defense air-only targeting implemented and tested).
  - (d) `python -u evaluate.py` completed with splash defenses noticeably punishing stacked `barch` vs tanked `giant_barch`/`goblin_giant`.

## Current Milestone: M6 (BASELINES)
- **Attempt:** 1
- **Passed:** —
- **Failed:** —
- **Next action:** Implement at least 3 distinct rule-based strategies in `agents/`; update `evaluate.py` to run 100 seeded episodes per base per army per strategy, save `results/baselines.csv`, print summary table (`mean destruction %`, `3-star rate`), and identify best baseline; verify results are not all 0% or 100%.
