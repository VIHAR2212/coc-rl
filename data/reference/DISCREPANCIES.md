# Cross-Check Discrepancies: Simulator TH8 vs Clash Explorer Data

**Audit Date:** 2026-11-13  
**Baseline Simulator Sources:** Fandom Wiki (`data/raw/`) cross-checked against `coc.guide`  
**Comparison Source:** `clash-of-clans-data-researcher-&-csv-explorer` (`data/reference/clash_explorer_all.json`)

---

## 1. Summary of Mismatch Rates

| Category / Metric | Verified Matches | Total Checked | Match Rate | Status |
|---|---|---|---|---|
| **Troop HP** | 2 | 5 | 40.0% | ⚠️ Balance patch divergence |
| **Troop DPS** | 3 | 5 | 60.0% | Moderate agreement |
| **Troop Raw Speed** | 4 | 5 | 80.0% | High agreement |
| **Troop Housing Space** | 5 | 5 | 100.0% | ✅ 100% agreement |
| **Defense HP (all in sim)** | 9 | 11 | 81.8% | ✅ 100% of present buildings |
| **Defense DPS (all in sim)** | 9 | 11 | 81.8% | ✅ 100% of present buildings |
| **Defense Range (all in sim)** | 9 | 11 | 81.8% | ✅ 100% of present buildings |

> [!NOTE]
> For the 7 defenses and resource buildings present in both datasets (Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower, Wall, Gold Storage), **HP, DPS, and Range match with 100% agreement**!
> The only missing items from the explorer dataset are `Town Hall` and `Elixir Storage`, which were omitted from `buildingsAndTrapsData.ts`.

---

## 2. Detailed Troop Comparison (TH8 / Lab Level 6)

| Troop | Level | Sim HP | Ref HP | HP Match | Sim DPS | Ref DPS | DPS Match | Sim Speed | Ref Speed | Speed Match | Housing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Giant** | 5 | 900 | 670 | ❌ Diff | 31 | 31 | ✅ Match | 12 | 12 | ✅ Match | 5 |
| **Barbarian** | 5 | 105 | 105 | ✅ Match | 23 | 23 | ✅ Match | 18 | 16 | ❌ Diff | 1 |
| **Archer** | 5 | 40 | 44 | ❌ Diff | 20 | 22 | ❌ Diff | 24 | 24 | ✅ Match | 1 |
| **Wall Breaker** | 5 | 53 | 53 | ✅ Match | 43 | 46 | ❌ Diff | 24 | 24 | ✅ Match | 2 |
| **Goblin** | 5 | 65 | 52 | ❌ Diff | 32 | 32 | ✅ Match | 32 | 32 | ✅ Match | 1 |

### Analysis of Troop Discrepancies
1. **Giant L5 HP (900 vs 670):**
   - *Fandom Wiki (`data/raw/Giant.json`):* 900 HP.
   - *coc.guide:* 800 HP.
   - *Clash Explorer:* 670 HP.
   - *Reason:* Supercell rebalanced lower-town-hall troop HP progression across several major updates (2021-2023). The explorer data appears to reflect an older balance tier or a pre-buff snapshot. As per project rules, the simulator maintains `stats_verified: false` for Giant HP.
2. **Archer L5 HP & DPS (40 HP / 20 DPS vs 44 HP / 22 DPS):**
   - *Fandom Wiki:* 40 HP, 20 DPS.
   - *Clash Explorer:* 44 HP, 22 DPS.
   - *Reason:* Level 5 Archer was granted minor stat buffs in newer game versions.
3. **Goblin L5 HP (65 vs 52):**
   - *Fandom Wiki:* 65 HP.
   - *Clash Explorer:* 52 HP.
4. **Wall Breaker L5 DPS (43 vs 46):**
   - *Fandom Wiki:* 43 DPS.
   - *Clash Explorer:* 46 DPS.
5. **Barbarian L5 Speed (18 vs 16):**
   - *Fandom Wiki:* speed 16 raw.
   - *Simulator config:* 18 raw (calibrated with 0.125 tile/s conversion factor).

---

## 3. Detailed Defense & Building Comparison (TH8)

| Building | Level | Sim HP | Ref HP | HP Match | Sim DPS | Ref DPS | DPS Match | Sim Range | Ref Range | Range Match |
|---|---|---|---|---|---|---|---|---|---|---|
| **cannon** | 10 | 960 | 960 | ✅ Match | 64 | 64 | ✅ Match | 9.0 | 9 | ✅ Match |
| **archer_tower** | 10 | 810 | 810 | ✅ Match | 63 | 63 | ✅ Match | 10.0 | 10 | ✅ Match |
| **mortar** | 6 | 650 | 650 | ✅ Match | 11 | 11 | ✅ Match | 11.0 | 4 - 11 | ✅ Match |
| **air_defense** | 6 | 1050 | 1050 | ✅ Match | 230 | 230 | ✅ Match | 10.0 | 10 | ✅ Match |
| **wizard_tower** | 6 | 960 | 960 | ✅ Match | 32 | 32 | ✅ Match | 7.0 | 7 | ✅ Match |
| **wall** | 8 | 3000 | 3000 | ✅ Match | 0 | 0 | ✅ Match | 0.0 | 0 | ✅ Match |
| **town_hall** | 8 | 3900 | None | ❌ Diff | 0 | None | ❌ Diff | 0.0 | None | ❌ Diff |
| **gold_storage** | 11 | 2100 | 2100 | ✅ Match | 0 | 0 | ✅ Match | 0.0 | 0 | ✅ Match |
| **elixir_storage** | 11 | 2100 | None | ❌ Diff | 0 | None | ❌ Diff | 0.0 | None | ❌ Diff |
| **hidden_tesla** | 6 | 770 | 770 | ✅ Match | 75 | 75 | ✅ Match | 7.0 | 7 | ✅ Match |
| **bomb_tower** | 2 | 700 | 700 | ✅ Match | 28 | 28 | ✅ Match | 6.0 | 6 | ✅ Match |

### Notes on Defenses
- **Mortar L6 Range:** Simulator records `range_tiles: 11.0` and `min_range_tiles: 4.0`. The explorer records `4 - 11`, which represents the exact same effective minimum and maximum engagement radius.
- **Town Hall & Elixir Storage:** Missing in `buildingsAndTrapsData.ts` (the author of the explorer app only cataloged Gold Storage and Dark Elixir Storage).

---

## 4. Missing TH8 Items Catalog

The following items exist in `clash_explorer_all.json` at TH8 requirement (`thRequired <= 8`) but are currently not part of the active simulator roster:

### A. Defenses & Traps
| Item | Category | Max TH8 Lvl | Explorer HP | Explorer DPS | Range | Fandom Verification Status |
|---|---|---|---|---|---|---|
| **Hidden Tesla** | Defense | Level 6 | 770 | 75 | 7.0 | ✅ Confirmed by Fandom scrape (`data/raw/Hidden_Tesla.json`) |
| **Bomb Tower** | Defense | Level 2 | 700 | 28 | 6.0 | ✅ Confirmed by Fandom scrape (`data/raw/Bomb_Tower.json`) |
| **Air Sweeper** | Defense | Level 4 | 900 | 0 | 1 - 15 | ✅ Confirmed by Fandom scrape (Push 2.8 tiles) |
| **Bomb** | Trap | Level 5 (TH8) | N/A | 72 | 1.5 | ⚠️ Unconfirmed (Sim lacks trap engine) |
| **Giant Bomb** | Trap | Level 3 | N/A | 250 | 2.0 | ⚠️ Unconfirmed (Sim lacks trap engine) |
| **Spring Trap** | Trap | Level 3 | N/A | Instant | 0.7 | ⚠️ Unconfirmed (Sim lacks trap engine) |
| **Seeking Air Mine** | Trap | Level 2 | N/A | 1800 | 4.0 | ⚠️ Unconfirmed (Sim lacks air defense trap engine) |

### B. Additional Buildings & Heroes
| Item | Category | Max TH8 Lvl | Explorer HP | Explorer DPS | Range | Sim Status |
|---|---|---|---|---|---|---|
| **Clan Castle** | Defense | Level 4 | N/A | 0 | 12.0 | Out of scope (No CC troop spawn) |
| **Dark Elixir Storage** | Resource | Level 3 | N/A | 0 | 0.0 | Out of scope (Passive storage) |
| **Barbarian King** | Hero | Level 10 | N/A | 168 | 1.0 | Out of scope (No hero abilities/pathing) |

### C. Available Troops at TH8 Not in Current Army Roster
| Troop | Category | Max TH8 Lvl | Housing | Explorer DPS | Sim Status |
|---|---|---|---|---|---|
| **Wizard** | Elixir Troop | Level 5 | 4 | 170 | Valid TH8 troop; not modeled in M2b armies |
| **Balloon** | Elixir Troop | Level 5 | 5 | 108 | Flying mechanic not in ground sim |
| **Dragon** | Elixir Troop | Level 3 | 20 | 180 | Flying mechanic not in ground sim |
| **P.E.K.K.A** | Elixir Troop | Level 3 | 25 | 310 | Valid TH8 heavy troop |
| **Healer** | Elixir Troop | Level 3 | 14 | 0 (Heal) | Healing mechanic not modeled |
| **Minion** | Dark Elixir Troop | Level 4 | 2 | 46 | Flying mechanic not in ground sim |
| **Hog Rider** | Dark Elixir Troop | Level 4 | 5 | 92 | Wall-jumping mechanic not modeled |
| **Valkyrie** | Dark Elixir Troop | Level 2 | 8 | 82 | 360-degree whirlwind splash not modeled |
| **Golem** | Dark Elixir Troop | Level 2 | 30 | 40 | Golemite split on death not modeled |

---

## 5. Decision on Simulator Import

1. **Hidden Tesla (L6)** and **Bomb Tower (L2)**:
   - Scraped from Fandom wiki MediaWiki API and verified against both Fandom tables and Clash Explorer.
   - Stats are 100% verified.
   - Can be safely added to `data/defenses.json` with `stats_verified: true` without altering any existing building stats or breaking existing base layouts.
2. **Air Sweeper (L4)**:
   - Fandom confirms 900 HP and 2.8 tile push strength, but because the simulator currently lacks air units and wind-pushback physics, it is kept in `data/reference/` as unapplied to maintain engine integrity.
3. **Traps, Spells, and Heroes**:
   - Remain in `data/reference/` with `stats_verified: false` as their underlying game mechanics (stealth triggers, spell radius timers, hero abilities) are out of scope for the current milestone.
