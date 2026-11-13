# Data Audit: Clash of Clans Data Researcher & CSV Explorer

**Audit Date:** 2026-11-13  
**Source Path:** `C:\Users\admin\Downloads\clash-of-clans-data-researcher-&-csv-explorer` (Read-Only)  
**Target Ingestion Directory:** `data/reference/`

---

## 1. Executive Summary & Architecture

The external repository `clash-of-clans-data-researcher-&-csv-explorer` is a static React / TypeScript web application built with Vite and Tailwind CSS.
- **Data Production Method:** The data is **entirely hardcoded as static TypeScript arrays** located in `src/data/*.ts`. It is **NOT** generated at runtime by AI model calls.
- **Runtime AI Check:** An audit of the codebase confirmed that although `@google/genai` was listed as a project dependency, **zero API calls** are executed in `src/`. The user interface merely filters, renders, and exports these precompiled static arrays.
- **Export Mechanism:** The app's CSV export functionality (`src/utils/csvExporter.ts`) serializes in-memory rows into standard RFC-4180 CSVs with 18 predefined columns. Prior to this audit, no CSV files had been saved to the user's `Downloads` folder.
- **Ingestion Result:** All 12 TypeScript source datasets were safely copied into `data/reference/raw_ts/` and normalized into:
  - `data/reference/clash_explorer_all.csv` (1,161 rows, 19 columns with origin)
  - `data/reference/clash_explorer_all.json` (1,161 records)
  - `data/reference/troop_behaviors.json` (41 unit behavior profiles)
  - `data/reference/conflicts.json` (10 balance patch / dispute records)

---

## 2. Dataset Files & Row Counts

The raw data comprises 10 primary stat files and 2 supplementary metadata files:

| File Name | Domain / Purpose | Rows / Records | Confidence Breakdown |
|---|---|---|---|
| `elixirTroops.ts` | Home Village regular elixir troops | 174 rows | 174 HIGH |
| `darkElixirTroops.ts` | Home Village dark elixir troops | 104 rows | 104 HIGH |
| `superTroops.ts` | Super troop variants | 89 rows | 89 HIGH |
| `builderBaseTroops.ts` | Builder Base army units | 164 rows | 164 HIGH |
| `defensesData.ts` | Home Village defenses (Cannons, Towers, etc.) | 228 rows | 175 HIGH, 41 LOW, 12 MEDIUM |
| `buildingsAndTrapsData.ts` | Storages, Traps, Teslas, Walls | 187 rows | 187 HIGH |
| `heroesData.ts` | Barbarian King, Archer Queen, Warden, etc. | 52 rows | 52 HIGH |
| `petsData.ts` | Hero pets (L.A.S.S.I, Owl, Yak, etc.) | 48 rows | 48 HIGH |
| `siegesData.ts` | Clan Capital & Town Hall 12+ Siege Machines | 18 rows | 18 HIGH |
| `equipmentData.ts` | Hero equipment & gear abilities | 215 rows | 215 HIGH |
| **Total Stat Rows** | | **1,161 rows** | **1,108 HIGH, 41 LOW, 12 MEDIUM** |
| `troopBehaviors.ts` | AI targeting, favorite targets, retarget rules | 41 units | Qualitative profiles |
| `conflicts.ts` | Documented stat discrepancies across balance patches | 10 records | Historical patch notes |

---

## 3. Coverage Analysis

### By Village
- **Home Village:** 997 rows (85.9%)
- **Builder Base:** 164 rows (14.1%)
- **Clan Capital:** 0 rows (0.0% — Clan Capital troops and buildings are not modeled)

### By Category
| Category | Row Count | Village | Coverage Notes |
|---|---|---|---|
| Defense | 228 | Home Village | Comprehensive from TH1 to TH17 |
| Hero Equipment | 215 | Home Village | Modern equipment (Giant Gauntlet, Spiky Ball, etc.) |
| Elixir Troop | 174 | Home Village | Levels 1 through max per troop |
| Builder Base Troop | 164 | Builder Base | Complete Builder Hall 1-10 troop trees |
| Dark Elixir Troop | 104 | Home Village | Minion, Hog Rider, Valkyrie, Golem, Witch, etc. |
| Super Troop | 89 | Home Village | Boosted versions with special abilities |
| Hero | 52 | Home Village | BK, AQ, GW, RC, Minion Prince |
| Hero Pet | 48 | Home Village | All 12 pets |
| Trap | 26 | Home Village | Bombs, Spring Traps, Giant Bombs, Air Mines |
| Army Building | 23 | Home Village | Army Camps, Blacksmith |
| Resource Building | 20 | Home Village | Gold Storage, Dark Elixir Storage |
| Siege Machine | 18 | Home Village | Wall Wrecker, Battle Blimp, Stone Slammer, etc. |
| Spells | 0 | - | **Omitted** (No spell data present in the explorer) |

### By Town Hall Level Required
The dataset covers Town Hall requirements from TH1 through TH18:
- **TH 1:** 7 rows
- **TH 2:** 13 rows
- **TH 3:** 23 rows
- **TH 4:** 27 rows
- **TH 5:** 31 rows
- **TH 6:** 41 rows
- **TH 7:** 64 rows
- **TH 8:** 78 rows
- **TH 9:** 107 rows
- **TH 10:** 84 rows
- **TH 11:** 92 rows
- **TH 12:** 93 rows
- **TH 13:** 96 rows
- **TH 14:** 128 rows
- **TH 15:** 116 rows
- **TH 16:** 71 rows
- **TH 17:** 54 rows
- **TH 18:** 36 rows

---

## 4. Source Citations & Confidence Ratings

- **Rows with Source Citations:** 1,161 / 1,161 (100.0%)
- **Distinct Source URLs:** 255 unique citations across `clashofclans.fandom.com` and `coc.guide`.
- **Confidence Ratings:**
  - `HIGH`: 1108 rows (95.4%) — corroborated across multiple wiki revisions.
  - `LOW`: 41 rows (3.5%) — flagged due to balance patch divergence (primarily early Cannon / Archer Tower rebalances).
  - `MEDIUM`: 12 rows (1.0%) — approximate values undergoing calibration.

---

## 5. Schema & Field Definitions

Each normalized row in `data/reference/clash_explorer_all.csv` and `.json` contains:
1. `name` (string): Common display name of the troop, defense, hero, or trap.
2. `village` (string): Home Village or Builder Base.
3. `category` (string): Defense, Elixir Troop, Dark Elixir Troop, Hero, Trap, etc.
4. `level` (int): Unit or building upgrade level.
5. `town hall (or building) level required` (int/string): Minimum Town Hall or Laboratory level.
6. `hitpoints` (int/string): Maximum health at this level (string when documenting patch conflict).
7. `damage per second` (int/float/string): DPS metric.
8. `damage per hit` (int/float/string): Damage dealt per single attack cycle.
9. `attack speed (seconds between attacks)` (float): Attack cooldown in seconds.
10. `range (tiles)` (float/string): Engagement radius in tiles (or min-max range string).
11. `footprint (tiles, e.g. 3x3)` (string): Physical grid dimension on the battlefield.
12. `housing space (troops)` (int): Army camp occupancy.
13. `movement speed` (int): Raw movement speed scalar.
14. `ground/air` (string): Targeting capability (Ground Only, Air & Ground, etc.).
15. `favorite target` (string): AI priority target (Defenses, Resources, Walls, Any).
16. `special ability or effect at this level` (string): Qualitative ability description.
17. `source URLs` (string): Semicolon-delimited source citations.
18. `confidence` (string): HIGH, MEDIUM, or LOW verification status.
19. `origin` (string): Source file path relative to project root.
