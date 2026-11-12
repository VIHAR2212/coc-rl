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

## Current Milestone: M5 (DEFENSE REALISM)
- **Attempt:** 1
- **Passed:** —
- **Failed:** —
- **Next action:** Implement Mortar min range & splash, Wizard Tower splash, Air Defense air-only targeting, and attack-speed based shots with projectile delay; check if TH8 flying troops are in wiki/data or skipped; add 1 unit test per mechanic; run `pytest -q`, `check_env`, `evaluate.py`.
