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

## Milestone M6 (BASELINES)
- **Status:** PASSED (Attempt 1)
- **Passed:**
  - (a) 3 rule-based strategies in `agents/`: `left_wave` (`agents/rule_based.py`), `surround` (`agents/surround.py`), `smart_funnel` (`agents/smart_funnel.py`) via `agents/helpers.py` and `agents/__init__.py`.
  - (b) `python -u evaluate.py` ran 100 seeded episodes per base per army per strategy (7200 episodes in 1421.3s) and saved `results/baselines.csv`.
  - (c) Non-degenerate results across bases/armies/strategies (`0.0%` to `100.0%`).
  - (d) Summary table printed; best baseline overall is `left_wave` (`42.75%` mean destruction, `25.00%` 3-star rate), vs `smart_funnel` (`28.86%`, `16.62%`) and `surround` (`23.06%`, `12.50%`).
  - `pytest -q` (`17 passed in 21.34s`) and `check_env OK`.

## Milestone M7 (RL)
- **Status:** PASSED (Attempt 1)
- **Passed:**
  - (a) `sb3_contrib` `MaskablePPO` (`sim/rl_wrapper.py: ActionMaskCoCEnv` + `CoCFeatureExtractor`) with exact deploy/wait action masks and TensorBoard logging (`runs/m7_stage1_single_1`, `runs/m7_stage2_split_0`). Trained Stage 1 on single base (`base03.json`, `25,000` steps) then Stage 2 on train split (`base01..base04`, `75,000` steps). Held out `base05.json` and `base06.json`.
  - (b) `train_ppo.py` and `evaluate_rl.py` ran end-to-end, saving `models/ppo_stage1_single.zip`, `models/ppo_coc_v1.zip`, `results/reward_curves.png`, and `results/rl_vs_baselines.csv`.
  - (c) Evaluated 100 seeded episodes per held-out `(base, army)` pair (`800` episodes per agent).
  - (d) Held-out mean destruction %: `maskable_ppo = 31.94%` vs `left_wave (best baseline) = 24.07%` vs `random_masked = 12.34%`. Beats random (+19.60 pp) and best baseline (+7.87 pp); logged in `REWARD_LOG.md`.

## Current Step: FINAL_REPORT.txt
- **Next action:** Gather exact git hashes and final test/eval results, write `FINAL_REPORT.txt`, commit and push to `origin/main`.
