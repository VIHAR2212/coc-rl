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

## Milestone M1e (CITATION SPOT-CHECK & TRUSTWORTHINESS AUDIT)
- **Status:** PASSED (Attempt 1)
- **Passed:**
  - (1) **Stratified Reproducible Sampling:** Sampled 150 rows from `data/reference/clash_explorer_all.csv` proportional to stratum size across `(village, category, thRequired)` using `seed=42` (129 Home Village, 21 Builder Base across 10 unit/building categories).
  - (2) **Live URL Verification & Caching:** Wrote `scripts/citation_spot_check.py` with 1.0s rate limiting and local caching (`data/raw/fandom_cache/`, `data/raw/cocguide_cache/`). Evaluated whether Level, HP, and DPS in each row matched the cited page.
    * Overall result: **53 matches (35.3%)**, **89 mismatches (59.3%)**, **7 unreachable URLs (4.7%)**, **1 page lacking value (0.7%)**.
    * Source sites: Fandom (35.6% match over 149 citations), coc.guide (15.3% match over 98 citations), third-party mirrors (0% match / dead links).
  - (3) **Audit Report (`data/reference/CITATION_CHECK.md`):**
    * Documented match rates across all categories (e.g. Defense 60.0%, Elixir Troops 58.3%, Hero Equipment 0.0%, Super Troops 0.0%).
    * Analyzed `"confidence": "HIGH"` labels: **NOT justified** (147/150 rows labeled HIGH, yet only 35.4% matched). Source app creator assigned HIGH confidence blanketly without validating against live pages or accounting for patch drifts or string placeholders.
    * Detailed 10 concrete mismatch examples with row vs page values and root cause analysis.
  - (4) **Troop Level & Discrepancy Breakdown:**
    * In simulator (Fandom Lab 6): Giant, Barbarian, Archer, Goblin, and Wall Breaker are all **Level 5**.
    * In explorer data: Giant, Barbarian, Archer, and Goblin are listed at **Level 6** for TH8 because the author mistakenly mapped Laboratory 6 to Level 6 (instead of Lab 5 -> L4, Lab 6 -> L5).
    * Even comparing at the **same level (Level 5)**, there are **real underlying stat disagreements** due to balance patches: Giant HP (900 vs 670, a 230-HP gap), Archer (40 HP / 20 DPS vs 44 HP / 22 DPS), Goblin (65 vs 52 HP), and Wall Breaker (43 vs 46 DPS), while Barbarian matches exactly (105 HP / 23 DPS).
  - (5) **Verification & Integrity:** Zero simulator changes, zero stat changes. `pytest -q` -> `20 passed in 21.21s`, `check_env` passed with zero errors.

## Current Step: STAGE 1 (M7b Part A) -> COMPLETED. Proceeding to STAGE 2 (M5b).
- **Stage 1 (M7b Part A) Status:** COMPLETED
  - (1) Determinism & Seed Variance Check: Ran 100 seeded episodes across 16 held-out pairs (`base07`..`base10` x 4 armies) for all 5 agents. Non-zero variance confirmed across 10-14 of 16 pairs (invariants are 0% or 100% destruction).
  - (2) Held-Out Evaluation (`results/m7b_partA.csv`):
    * `maskable_ppo`: 31.78% dest [95% CI 19.51, 45.62], 0.57 stars [0.18, 1.04], 5.38% 3-star [0.00, 15.00]
    * `left_wave`: 27.32% dest [95% CI 13.53, 43.27], 0.70 stars [0.25, 1.23], 6.25% 3-star [0.00, 18.75]
    * `smart_funnel`: 22.82% dest [95% CI 11.29, 36.67], 0.41 stars [0.10, 0.81], 4.19% 3-star [0.00, 12.56]
    * `surround`: 9.77% dest [95% CI 3.77, 17.82], 0.11 stars [0.00, 0.32], 0.00% 3-star
    * `random_masked`: 8.69% dest [95% CI 3.78, 14.94], 0.03 stars [0.00, 0.09], 0.00% 3-star
    * **PPO vs Best Baseline (`left_wave`):** Beats on destruction (+4.46 pp [95% CI +0.01, +9.10]); DOES NOT beat on stars (-0.128 stars [95% CI -0.309, +0.008]).
  - (3) PPO Action Diagnostics (`results/ppo_action_diagnostics.csv`):
    * Evaluated models: `models/ppo_m7b_seed42.zip..44.zip` (trained 2026-11-12).
    * Single sector collapse (>90% army in one sector): 0 of 16 pairs. Single sector fraction is 0.0 across 15 pairs and 0.33 on 1 pair (`barch` on `base08`).
    * Distinct sectors per episode: 2.00 to 3.53 sectors.
    * Action entropy: 1.695 to 3.361 nats.
    * Wall Breaker deployment fraction: 100% when available in army (`goblin_giant` and `mixed_wb`), at average step 12.8 to 32.1.
  - (4) TH8 Level Check (`data/TH8_LEVEL_CHECK.md`): Verified from Fandom Laboratory & Town Hall tables that Giant, Barbarian, Archer, Goblin, and Wall Breaker are strictly Level 5 at TH8 (Laboratory Level 6). Stop Condition 2 is NOT triggered.
  - (5) Integrity Checks: `pytest -q` -> 20 passed in 15.63s; `check_env` BOTH OK.
- **Next action:** Commit Stage 1 deliverables, push to origin/main, then start STAGE 2 (M5b).
