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

## Milestone M7b (CREDIBILITY UPGRADE & RENDER POLISH)
- **Status:** COMPLETE
- **Passed:**
  - (1) **Legitimate seed variance:** Verified that policies on previous deterministic sim had zero variance across seeds within a pair. Added seeded sub-tile spawn jitter (`uniform(-0.3, 0.3)`) and initial defense cooldown phase offsets (`uniform(0, attack_speed)`) in `sim/env.py`. 22/24 pairs now show genuine across-seed variance.
  - (2) **Expanded held-out layout pool:** Added 4 new diverse TH8 layouts (`base07.json` Southern Teaser, `base08.json` Moated Ring, `base09.json` Four-Quadrant Islands, `base10.json` Wide Bastion). All 10 bases pass `validate_base.py`. Training split cleanly excludes trivial `base01.json` (`TRAIN_BASES = ["base02.json", "base03.json", "base04.json"]`), holding out 6 bases x 4 armies = 24 independent pairs.
  - (3) **Observation & reward tuning:** Added 6th grid channel (`is_town_hall`) to observation space so RL can localize the TH. Added stars-aware reward shaping: `+25.0` cliff bonus at 50% destruction, `+25.0` additional TH bonus (`+75.0` total), `+50.0` at 100% destruction, `-0.05` wait penalty. Logged in `REWARD_LOG.md`.
  - (4) **Extended multi-seed training:** Trained MaskablePPO across 3 random seeds (`42, 43, 44`) with 25k Stage 1 steps and 500k Stage 2 steps each (`SubprocVecEnv(4)`, total 1.575M steps) with TensorBoard logging, saving models and multi-seed curves to `results/reward_curves.png`.
  - (5) **Render polish:** Updated `CoCEnv.render()` with distinct sizes per troop type (Giant largest, radius 9; Barbarian 6; Archer/WB/Goblin 5), HP bars on wounded troops, bottom-left troop legend, and "time left:" HUD label. Re-recorded `docs/baseline_attack.gif` at 250ms duration and added `docs/ppo_attack.gif` on held-out `base06.json`.
  - (6) **Full 24-pair evaluation & bootstrap CIs:** Evaluated 100 seeded episodes per pair for all 5 agents (12,000 total episodes, saved to `results/rl_vs_baselines.csv` and `results/rl_vs_baselines_pairs.csv`):
    * `maskable_ppo`:  **31.15%** dest [95% CI 21.61, 41.40], **0.46** stars [0.18, 0.80], **3.58%** 3-star [0.00, 10.00]
    * `left_wave`:     **26.12%** dest [95% CI 16.00, 37.42], **0.53** stars [0.21, 0.92], **4.17%** 3-star [0.00, 12.50]
    * `smart_funnel`: **20.33%** dest [95% CI 12.21, 30.24], **0.28** stars [0.07, 0.56], **2.79%** 3-star [0.00, 8.38]
    * `surround`:     **10.73%** dest [95% CI  5.75, 16.76], **0.07** stars [0.00, 0.21], **0.00%** 3-star
    * `random_masked`:  **9.94%** dest [95% CI  5.72, 14.81], **0.02** stars [0.00, 0.06], **0.00%** 3-star
    * **Honest comparison:** PPO beats best baseline on destruction (+5.02 pp [95% CI +1.96, +8.29]) and beats random (+21.21 pp). PPO does **not** beat `left_wave` on stars (0.46 vs 0.53, delta -0.070 [-0.204, +0.042]).
  - `pytest -q`: `20 passed in 68.74s`; `check_env BOTH OK`.

## Milestone M1d (DATA RESEARCHER & CSV EXPLORER IMPORT)
- **Status:** PASSED (Attempt 1)
- **Passed:**
  - (1) **Data Audit (`data/reference/DATA_AUDIT.md`):** Audited `C:\Users\admin\Downloads\clash-of-clans-data-researcher-&-csv-explorer` (read-only). Confirmed data is 100% hardcoded in static TypeScript arrays in `src/data/*.ts` (zero runtime AI calls, no existing CSV exports). Cataloged 1,161 rows across 12 files (997 Home Village, 164 Builder Base, 0 Clan Capital, 0 Spells) spanning TH1-TH18 with 100% source citations (255 distinct URLs).
  - (2) **Normalized Reference Exports:** Wrote `scripts/export_all_reference.mjs` and generated:
    * `data/reference/clash_explorer_all.csv` (1,161 rows, 19 standard columns with `origin`).
    * `data/reference/clash_explorer_all.json` (1,161 structured records).
    * `data/reference/troop_behaviors.json` (41 unit behavior profiles).
    * `data/reference/conflicts.json` (10 balance patch / conflict records).
  - (3) **Cross-Check (`data/reference/DISCREPANCIES.md`):** Cross-checked current TH8 simulator entities against explorer data:
    * Defenses & Buildings: 7/7 present buildings (Cannon L10, Archer Tower L10, Mortar L6, Air Defense L6, Wizard Tower L6, Wall L8, Gold Storage L11) match **100.0% on HP, DPS, and Range** (Mortar min-max range 4-11 matches). Town Hall and Elixir Storage omitted from explorer source.
    * Troops: Housing space 5/5 (100%), Speed 4/5 (80%), DPS 3/5 (60%), HP 2/5 (40%). Discrepancies traced to balance patch revisions (e.g. Giant HP 900 vs 670, Archer 40 vs 44 HP).
  - (4) **Missing TH8 Items Evaluation:**
    * Fandom wiki MediaWiki API scrapes completed via `scripts/scrape_fandom.py`: `Hidden_Tesla.json`, `Bomb_Tower.json`, `Air_Sweeper.json`.
    * Confirmed Hidden Tesla (L6: HP 770, DPS 75, Range 7.0) and Bomb Tower (L2: HP 700, DPS 28, Range 6.0, Splash 1.5); added to `data/defenses.json` with `stats_verified: true` without altering existing stats.
    * Unapplied items (Air Sweeper push mechanics, Traps, Heroes, other troops) cataloged in `data/reference/unconfirmed_th8_items.json` with `stats_verified: false` and NOT loaded into the simulator.
  - (5) **Verification:** `pytest -q` -> `20 passed in 30.76s`, `check_env` passed with zero errors, `python evaluate.py` completed across all 120 combos (600 episodes) with zero regressions.

## Current Step: FINAL_REPORT.txt
- **Next action:** Update `FINAL_REPORT.txt` with M7b evidence, commit in small steps, and push to `origin/main`.
