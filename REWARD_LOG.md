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

