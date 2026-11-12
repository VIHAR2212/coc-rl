# Reward & RL Design Log (REWARD_LOG.md)

Log of every observation, action-space, and reward-design iteration for Milestone M7 (`MaskablePPO`), including why each change was made and what worked or broke.

---

## Attempt 1 — Masked Edge-Sector Discrete Action Space + Baseline Reward
- **Action space (`sim/rl_wrapper.py: ActionMaskCoCEnv`):**
  - Replaced raw `MultiDiscrete([6, 44, 44])` (`11,616` combinations where `x`/`y` cannot be jointly masked against irregular interior `_deploy_mask`) with `Discrete(1 + 5 * 16) = Discrete(81)`:
    - `0` = Wait
    - `1 + troop_idx * 16 + sector_idx` = deploy troop `troop_idx` on valid perimeter tiles (`edge_ring_tiles`) in angular sector `sector_idx` (`0..15`), rotating tile cursor within the sector to avoid stacking all units onto a single splash tile.
  - **Action mask (`action_masks()`):** Masks out depleted troop types (`army_left[k] == 0`), empty perimeter sectors, and Wait before any troop is deployed while troops remain. Guarantees zero invalid-deploy penalties (`-0.05`).
- **Observation space:**
  - Unchanged `CoCEnv` `Dict({"grid": (5, 44, 44), "army": (7,)})`, paired with lightweight `CoCFeatureExtractor` (`Conv2d(5->16->32->32)` + `AdaptiveAvgPool2d(4, 4)` + `army` MLP -> `160` dims) so MaskablePPO trains fast on 2 CPU cores.
- **Reward (`shaping_mode="baseline"`):**
  - Unmodified `CoCEnv` reward: `(destruction - prev_destruction) * 100 + 50 * th_destroyed_once - 0.01` per step.
- **Train / Held-out Split:**
  - Stage 1 (single base): `base03.json` across all 4 TH8 armies (`25,000` timesteps).
  - Stage 2 (train split): `base01.json`, `base02.json`, `base03.json`, `base04.json` across all 4 TH8 armies (`80,000` timesteps), TensorBoard logged to `runs/`.
  - Held-out evaluation bases (never seen during training): `base05.json` (unwalled defenses-outside) and `base06.json` (130-wall mixed base).
- **Outcome (Attempt 1 — PASSED):**
  - Held-out bases (`base05.json`, `base06.json`), `100` seeded episodes per `(base, army)` (`800` episodes per agent, `results/rl_vs_baselines.csv`):
    - `maskable_ppo`: **`31.94%`** mean destruction (`base05`: `44.44%`/`3.70%`/`33.33%`/`29.63%`; `base06`: `40.74%`/`18.52%`/`48.15%`/`37.04%`), `0.00` mean stars.
    - `left_wave` (best M6 baseline): **`24.07%`** mean destruction (`base05`: `48.15%`/`0.00%`/`44.44%`/`25.93%`; `base06`: `29.63%`/`0.00%`/`22.22%`/`22.22%`), `0.25` mean stars.
    - `random_masked`: **`12.34%`** mean destruction (`base05`: `24.48%`/`22.22%`/`23.07%`/`22.96%`; `base06`: `2.59%`/`0.00%`/`2.04%`/`1.37%`), `0.00` mean stars.
  - Beats `random_masked` by `+19.60 pp` and beats best baseline `left_wave` by `+7.87 pp` (especially nearly doubling destruction on unseen walled `base06.json`). Note `CoCFeatureExtractor` + edge-sector `Discrete(81)` masking converged without needing `shaping_mode="tactical"` (kept `"tactical"` unactivated for comparison/future work).
- **What broke / limitations discovered in M7 Attempt 1 audit (motivated M7b):**
  1. `CoCEnv` and deterministic policies (`maskable_ppo`, `left_wave`) had `std = 0.0` across all 100 seeds per `(base, army)` pair — `800` episodes actually represented only `8` distinct `(base, army)` samples (`base05`, `base06` x 4 armies).
  2. `maskable_ppo` got **`0.00` mean stars** (vs `left_wave` `0.25` mean stars) despite higher mean destruction (`31.94%` vs `24.07%`): it reached `44%–48%` repeatedly without crossing the `50%` 1-star threshold, and `CoCEnv`'s 5 grid channels made Town Hall indistinguishable from Gold/Elixir Storages.
  3. Stage 2 included trivial `base01.json` (9 buildings), wasting `25%` of training budget on an auto-3-star layout.

---

## M7b — Credibility Upgrade: Stars-Aware Reward, TH Grid Channel, 500k Multi-Seed Training, 6 Held-Out Bases
- **Fixes in `sim/env.py`:**
  - Added reproducible seeded sub-tile spawn jitter (`uniform(-0.3, 0.3)` around tile center in `_spawn`) and initial defense firing-phase offset (`uniform(0, attack_speed)` in `reset`), so different seeds produce genuine variance while remaining deterministic given `seed`.
- **Observation & Action space (`sim/rl_wrapper.py`):**
  - Added a **6th grid channel (`is_town_hall`)** so `CoCFeatureExtractor` can locate the Town Hall independently from storages on unseen layouts.
  - Updated `CoCFeatureExtractor` to a faster stride-4 + stride-2 CNN (`6->16->24`) for 500k-step CPU training.
  - Excluded trivial `base01.json` from `TRAIN_BASES` -> `["base02.json", "base03.json", "base04.json"]`.
  - Added 4 diverse TH8 held-out layouts (`base07.json`–`base10.json`), expanding evaluation to **6 held-out bases x 4 armies = 24 independent `(base, army)` pairs**.
- **Stars-aware reward (`shaping_mode="stars_aware"`):**
  - Base `CoCEnv` reward (`+delta_destruction * 100`, `+50` TH, `-0.01/step`) PLUS:
    - **`+25.0`** upon crossing `50%` destruction (`prev_dest < 0.5 <= destruction`, 1-star cliff)
    - **`+25.0`** additional Town Hall bonus (`total +75.0` for TH star)
    - **`+50.0`** upon reaching `100%` destruction (3-star completion bonus)
    - **`-0.05`** penalty for choosing `Wait` while troops remain in `army_left`
  - **Why:** Encourages pushing attacks over 50% and targeting the Town Hall sector instead of stopping at ~45% peripheral percentage.
- **Training schedule:** 3 random seeds (`42, 43, 44`), each running Stage 1 (`base03.json`, `25,000` steps) followed by Stage 2 (`base02..base04`, `500,000` steps) with TensorBoard logging.
- **Outcome (M7b):** Pending 3-seed training and 24-pair evaluation.

