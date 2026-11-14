# M9 Expert Demonstrations & Replay Verification (`left_wave`)

## 1. Overview and Setup
- **Source Agent:** `left_wave` baseline (`agents/rule_based.py`).
- **Layouts Used:** Training bases only (`base02.json, base03.json, base04.json`). Held-out bases (`base07` to `base10`) were strictly excluded.
- **Armies:** All 7 TH8 compositions (`giant_barch, barch, goblin_giant, mixed_wb, mass_dragons, gowiva, hog_rush`).
- **Episode Seeds:** Seeds 1000 to 1049 (50 episodes per base/army pair, 1050 total episodes).
- **Total Recorded Steps:** 130,667 decision transitions.

---

## 2. Coordinate-to-Sector Mapping Mechanism
In `CoCEnv`, `left_wave` deploys units at discrete coordinate tuples `(troop_kind, x, y)` along the western map flank (`x in (0, 1, 2, 3)` with sinusoidal `y` wave offsets around the map center).

In the 209-action `ActionMaskCoCEnv` wrapper:
- Action `0` represents the `wait` decision.
- Actions `1..208` represent deploying troop $k \in [0..12]$ into one of 16 perimeter edge sectors $s \in [0..15]$ (`action = 1 + k * 16 + s`).
- Each sector $s$ consists of valid deployable tiles along the base boundary (`edge_ring_tiles(env)`), partitioned by center polar angle $\theta = \text{atan2}(y - 22, x - 22)$.

### Mapping Strategy
For each non-wait deploy action `(troop_kind, x, y)`:
1. Identify the troop index $k = \text{troop\_kind} - 1$.
2. Compute the minimum Euclidean distance between `(x, y)` and any tile $(t_x, t_y)$ currently assigned to sector $s$:
   $$\text{dist}(s) = \min_{(t_x, t_y) \in \text{tiles}[s]} \sqrt{(x - t_x)^2 + (y - t_y)^2}$$
3. Map to the sector $s$ that minimizes this tile distance:
   $$s^* = \arg\min_{s} \text{dist}(s)$$
4. Assign the discrete wrapper action $a = 1 + k \cdot 16 + s^*$.

---

## 3. Mapping Error & Mask Validity Diagnostics
- **Total Troop Deployments:** 101,925
- **Mean Mapping Distance:** **1.95 tiles**
- **Max Mapping Distance:** 5.00 tiles
- **Share of Deploys Mapping to a Masked Action:** **0/101925 (0.00%)**

> Because `left_wave` deploys along the western perimeter, all deployments fall directly adjacent to Sectors 0 and 15, which border the western map edge. All mapped actions are fully valid under `ActionMaskCoCEnv.action_masks()` throughout deployment.

---

## 4. Replay Test: Raw `left_wave` vs Replayed `ActionMaskCoCEnv`
To verify that mapping continuous deploys to discrete sector actions preserves battle dynamics, mapped wrapper actions were re-executed step-by-step in `ActionMaskCoCEnv` with identical seeds.

- **Mean Raw `left_wave` Destruction:** 62.05%
- **Mean Replayed Wrapper Destruction:** 59.92%
- **Overall Destruction Gap:** **-2.13 percentage points** (Requirement: loss $\le 10$ pp — **PASSED**).
- **Overall Stars Gap:** **-0.04 stars**

### Per-Pair Replay Results Table

| Base | Army | Episodes | Raw Dest % | Wrap Dest % | Dest Gap (pp) | Raw Stars | Wrap Stars | Stars Gap |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `base02.json` | `giant_barch` | 50 | 7.9% | 6.4% | -1.5 | 0.00 | 0.00 | +0.00 |
| `base02.json` | `barch` | 50 | 0.0% | 0.0% | +0.0 | 0.00 | 0.00 | +0.00 |
| `base02.json` | `goblin_giant` | 50 | 11.2% | 10.7% | -0.4 | 0.00 | 0.00 | +0.00 |
| `base02.json` | `mixed_wb` | 50 | 7.4% | 7.4% | +0.0 | 0.00 | 0.00 | +0.00 |
| `base02.json` | `mass_dragons` | 50 | 100.0% | 100.0% | +0.0 | 3.00 | 3.00 | +0.00 |
| `base02.json` | `gowiva` | 50 | 72.7% | 80.7% | +8.1 | 1.96 | 2.00 | +0.04 |
| `base02.json` | `hog_rush` | 50 | 53.6% | 47.7% | -5.9 | 0.88 | 0.28 | -0.60 |
| `base03.json` | `giant_barch` | 50 | 100.0% | 100.0% | +0.0 | 3.00 | 3.00 | +0.00 |
| `base03.json` | `barch` | 50 | 4.0% | 0.0% | -4.0 | 0.00 | 0.00 | +0.00 |
| `base03.json` | `goblin_giant` | 50 | 100.0% | 74.2% | -25.9 | 3.00 | 2.00 | -1.00 |
| `base03.json` | `mixed_wb` | 50 | 73.4% | 64.1% | -9.3 | 2.00 | 2.00 | +0.00 |
| `base03.json` | `mass_dragons` | 50 | 100.0% | 100.0% | +0.0 | 3.00 | 3.00 | +0.00 |
| `base03.json` | `gowiva` | 50 | 100.0% | 100.0% | +0.0 | 3.00 | 3.00 | +0.00 |
| `base03.json` | `hog_rush` | 50 | 100.0% | 100.0% | +0.0 | 3.00 | 3.00 | +0.00 |
| `base04.json` | `giant_barch` | 50 | 60.2% | 60.7% | +0.5 | 1.18 | 1.70 | +0.52 |
| `base04.json` | `barch` | 50 | 7.4% | 7.4% | +0.0 | 0.00 | 0.00 | +0.00 |
| `base04.json` | `goblin_giant` | 50 | 52.1% | 58.9% | +6.8 | 0.72 | 2.00 | +1.28 |
| `base04.json` | `mixed_wb` | 50 | 53.2% | 48.4% | -4.8 | 1.60 | 1.24 | -0.36 |
| `base04.json` | `mass_dragons` | 50 | 100.0% | 100.0% | +0.0 | 3.00 | 3.00 | +0.00 |
| `base04.json` | `gowiva` | 50 | 100.0% | 99.0% | -1.0 | 3.00 | 2.76 | -0.24 |
| `base04.json` | `hog_rush` | 50 | 100.0% | 92.7% | -7.3 | 3.00 | 2.54 | -0.46 |