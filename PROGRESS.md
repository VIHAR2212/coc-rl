# Progress Log

## STEP 0 (Precondition)
- **Status:** PASSED
- `data/armies.json` exists (200 housing capacity, 4 TH8 compositions).
- `python evaluate.py` ran (commit `cdbfe55`): `giant_barch` scored `100.0%` (`base01`), `70.4%` (`base03`), `74.1%` (`base04`), `33.3%` (`base06`), `14.8%` (`base05`), `3.7%` (`base02`).

## Milestone M3 (RENDER)
- **Status:** PASSED (Attempt 2)
- **Passed:**
  - (a) `CoCEnv.render()` (`rgb_array` + `human` with pygame); `scripts/record_demo.py` saved 13 PNG frames + `docs/baseline_attack.gif` (91 frames, `dest=70.4% stars=1`).
  - (b) `play_human.py --smoke-test` exited 0.
  - (c) `scripts/speed_sanity.py` printed all 5 troops' speeds and 20-tile times (flagged `speed_verified=False`, uncalibrated `0.125`).
  - `pytest -q`: `7 passed in 7.66s`; `check_env OK`.
- **Needs human check:** Visual inspection of `docs/baseline_attack.gif`, PNG frames in `docs/`, and interactive `play_human.py`.

## Current Milestone: M4 (WALLS AND PATHING)
- **Attempt:** 1
- **Passed:** —
- **Failed:** —
- **Next action:** Scrape `Wall` from Fandom wiki, add `wall` to `data/defenses.json`, implement 1x1 walls (excluded from destruction %), A* pathing, blocked-path wall breaking, and Wall Breaker targeting, add walls to 3+ bases, run M4 checks + `pytest -q` + `check_env`.
