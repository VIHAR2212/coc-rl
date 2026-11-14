# CoC-RL Battle Gallery: Side-by-Side Strategy Visualizations

Animated side-by-side battle recordings comparing the baseline **`left_wave`** (left panel) against trained **`MaskablePPO`** (right panel, `seed42`, deterministic actions) on held-out bases (`base07.json` to `base10.json`) across key TH8 army compositions (`giant_barch`, `mixed_wb`, `hog_rush`, `gowiva`) at **seed 0** (250 ms / frame).

---

## Featured Showcase Battles

The 4 most instructive animations are preserved in [`docs/showcase/`](../showcase/):

1. **PPO Victory ([`docs/showcase/ppo_win_base09_hog_rush.gif`](../showcase/ppo_win_base09_hog_rush.gif) - 444.2 KB):**
   - **Base:** `base09.json` | **Army:** `hog_rush`
   - **Left Wave:** 59.3% dest, 1★, Town Hall Alive
   - **MaskablePPO:** 100.0% dest, 3★, Town Hall Destroyed (**+40.7% dest, +2★**)
   - *Tactical Analysis:* PPO distributes Hog Riders across multiple sectors, allowing them to jump walls, clear defense towers independently without grouping into Mortar splash, and easily wipe the Town Hall.

2. **PPO Defeat ([`docs/showcase/ppo_loss_base08_gowiva.gif`](../showcase/ppo_loss_base08_gowiva.gif) - 610.6 KB):**
   - **Base:** `base08.json` | **Army:** `gowiva`
   - **Left Wave:** 100.0% dest, 3★, Town Hall Destroyed
   - **MaskablePPO:** 40.7% dest, 0★, Town Hall Alive (**-59.3% dest, -3★**)
   - *Tactical Analysis:* Demonstrates why PPO trails on stars with heavy ground armies. `left_wave` masses all Valkyries and Golems on a single flank, cutting directly through the core walls to the Town Hall for a complete 3-star wipe. PPO spreads its Golems and Valkyries around the perimeter, splitting its damage and stalling outside the walls with 0 stars.

3. **3-Star Wipe ([`docs/showcase/three_star_base10_giant_barch.gif`](../showcase/three_star_base10_giant_barch.gif) - 653.4 KB):**
   - **Base:** `base10.json` | **Army:** `giant_barch`
   - **Left Wave:** 100.0% dest, 3★, Town Hall Destroyed
   - **MaskablePPO:** 100.0% dest, 3★, Town Hall Destroyed (**Tie**)
   - *Tactical Analysis:* An open layout with few interior wall barriers allows both massed single-flank rushes and multi-sector perimeter deployments to overwhelm point defenses and wipe 100% of the base.

4. **Compartment Stalemate ([`docs/showcase/failure_base07_giant_barch.gif`](../showcase/failure_base07_giant_barch.gif) - 576.5 KB):**
   - **Base:** `base07.json` | **Army:** `giant_barch`
   - **Left Wave:** 11.1% dest, 0★, Town Hall Alive
   - **MaskablePPO:** 25.9% dest, 0★, Town Hall Alive (**0★ for both**)
   - *Tactical Analysis:* Heavily walled concentric compartments neutralize standard ground armies without jump or mass wall breakers. Both agents stall against the outer perimeter defenses and fail to breach the core.

---

## Summary of All 16 Battles

| Base | Army | Left Wave (Dest / Stars / TH) | PPO (Dest / Stars / TH) | Delta Dest | Delta Stars | Outcome | Animation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `base07.json` | `giant_barch` | 11.1% / 0★ / no-TH | 25.9% / 0★ / no-TH | +14.8% | +0 | **PPO WIN** | [base07_giant_barch.gif](base07_giant_barch.gif) |
| `base07.json` | `mixed_wb` | 0.0% / 0★ / no-TH | 18.5% / 0★ / no-TH | +18.5% | +0 | **PPO WIN** | [base07_mixed_wb.gif](base07_mixed_wb.gif) |
| `base07.json` | `hog_rush` | 51.9% / 1★ / no-TH | 85.2% / 2★ / TH | +33.3% | +1 | **PPO WIN** | [base07_hog_rush.gif](base07_hog_rush.gif) |
| `base07.json` | `gowiva` | 44.4% / 0★ / no-TH | 59.3% / 1★ / no-TH | +14.9% | +1 | **PPO WIN** | [base07_gowiva.gif](base07_gowiva.gif) |
| `base08.json` | `giant_barch` | 14.8% / 0★ / no-TH | 14.8% / 0★ / no-TH | +0.0% | +0 | **TIE** | [base08_giant_barch.gif](base08_giant_barch.gif) |
| `base08.json` | `mixed_wb` | 18.5% / 0★ / no-TH | 14.8% / 0★ / no-TH | -3.7% | +0 | **LW WIN** | [base08_mixed_wb.gif](base08_mixed_wb.gif) |
| `base08.json` | `hog_rush` | 100.0% / 3★ / TH | 100.0% / 3★ / TH | +0.0% | +0 | **TIE** | [base08_hog_rush.gif](base08_hog_rush.gif) |
| `base08.json` | `gowiva` | 100.0% / 3★ / TH | 40.7% / 0★ / no-TH | -59.3% | -3 | **LW WIN** | [base08_gowiva.gif](base08_gowiva.gif) |
| `base09.json` | `giant_barch` | 63.0% / 2★ / TH | 77.8% / 2★ / TH | +14.8% | +0 | **PPO WIN** | [base09_giant_barch.gif](base09_giant_barch.gif) |
| `base09.json` | `mixed_wb` | 37.0% / 1★ / TH | 81.5% / 2★ / TH | +44.5% | +1 | **PPO WIN** | [base09_mixed_wb.gif](base09_mixed_wb.gif) |
| `base09.json` | `hog_rush` | 59.3% / 1★ / no-TH | 100.0% / 3★ / TH | +40.7% | +2 | **PPO WIN** | [base09_hog_rush.gif](base09_hog_rush.gif) |
| `base09.json` | `gowiva` | 100.0% / 3★ / TH | 63.0% / 1★ / no-TH | -37.0% | -2 | **LW WIN** | [base09_gowiva.gif](base09_gowiva.gif) |
| `base10.json` | `giant_barch` | 100.0% / 3★ / TH | 100.0% / 3★ / TH | +0.0% | +0 | **TIE** | [base10_giant_barch.gif](base10_giant_barch.gif) |
| `base10.json` | `mixed_wb` | 55.6% / 2★ / TH | 55.6% / 2★ / TH | +0.0% | +0 | **TIE** | [base10_mixed_wb.gif](base10_mixed_wb.gif) |
| `base10.json` | `hog_rush` | 100.0% / 3★ / TH | 100.0% / 3★ / TH | +0.0% | +0 | **TIE** | [base10_hog_rush.gif](base10_hog_rush.gif) |
| `base10.json` | `gowiva` | 100.0% / 3★ / TH | 96.3% / 2★ / TH | -3.7% | -1 | **LW WIN** | [base10_gowiva.gif](base10_gowiva.gif) |

---

## Key Tactical Insights from the Gallery

1. **Core Penetration vs Perimeter Dispersion:** On layouts where `left_wave` breaks through outer walls (`base08` `gowiva`), massing all units along a single flank enables high-dps Valkyries to cut through to the Town Hall for a 3-star clear. In contrast, PPO's multi-sector deployments diffuse attack power across multiple compartments, stalling outside the core.
2. **Hog Rider Wall Bypass:** On `base09` `hog_rush`, PPO's distributed deployment around multiple defensive sectors enables Hog Riders to path cleanly between outer defenses and clear defensive towers without bunching into Mortar splash, achieving an uncontested 100% 3-star wipe (+40.7% over `left_wave`).
3. **Open Base Bulldozing:** On `base10` `giant_barch`, the wide open courtyard layout allows both strategies to overwhelm point defenses and achieve complete 100% 3-star wipes.
4. **Compartmentalized Stalemates:** On `base07`, heavy interior wall rings stop both `left_wave` and `PPO` `giant_barch` outside the core (0 stars for both), highlighting the difficulty of compartmented layouts for basic ground armies.