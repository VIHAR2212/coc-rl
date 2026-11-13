# Troops & Builder Base Housing Space Expansion

Expand the Clash Research Workbench to integrate the four missing Home Village troops (Thrower, Furnace, Ruin Witch, Super Yeti) and all 12 Builder Base troops with full per-level stats, housing space values, tactical behaviors, and multi-source citations inside the existing Troops explorer.

## User Review & Critical Decisions

> [!IMPORTANT]
> All scope and organization choices below were confirmed during interactive clarification and govern this expansion.

- **Confirmed Scope**: Add the missing Home Village troops (**Thrower**, **Furnace**, **Ruin Witch**, **Super Yeti**) alongside all **12 Builder Base Troops** (Raged Barbarian, Sneaky Archer, Boxer Giant, Beta Minion, Bomber, Baby Dragon, Cannon Cart, Night Witch, Drop Ship, Power P.E.K.K.A, Hog Glider, and Electrofire Wizard).
- **Confirmed Navigation Placement**: Integrate Builder Base Troops directly inside the existing **Troops** tab via an interactive troop-category segmented filter (`All`, `Elixir Troop`, `Dark Elixir Troop`, `Super Troop`, `Builder Base Troop`) rather than creating a separate top-level tab.
- **Confirmed Data Depth**: Collect complete per-level stat progressions (TH/BH unlock, Lab/Star Lab tier, HP, DPS, damage per hit, attack speed, range, footprint, housing space, movement speed, target type, favorite target, and special abilities), tactical behavior entries, and dual-source citations (`clashofclans.fandom.com`, `coc.guide`, and official patch notes).

---

## 1. Overview & Core Concept

- **What It Does**: Completes the full Troop & Housing Space ledger across both Home Village and Builder Base 2.0. Users can filter between Home Village Elixir (19 troops), Dark Elixir (13 troops), Super Troops (17 troops), and Builder Base Troops (12 troops), inspect exact housing space allocations, read AI/targeting behavior profiles, review patch discrepancies in the Audit Log, and export the unified 17-column CSV.
- **Target Audience**: Competitive base/army planners, spreadsheet analysts, and Clash of Clans researchers comparing unit efficiency per housing space across villages.
- **Key Value**: Resolves recent 2025–2026 troop additions (Thrower, Furnace, Ruin Witch, Super Yeti) and brings Builder Base 2.0's 12 troops into the same standardized schema using explicit housing space equivalents.

---

## 2. User Experience & Visual Design

- **Key User Flows**:
  1. Selecting the **Troops** tab reveals a compact segmented sub-filter bar (`All Troops`, `Elixir`, `Dark Elixir`, `Super`, `Builder Base`) paired with unit-name, Town/Builder Hall, and live search controls.
  2. Switching to **Builder Base** updates the unit dropdown automatically to the 12 Builder Base units and populates the data table with `Builder Base` village rows, Star Laboratory prerequisites, and per-troop housing space (`3` to `22`).
  3. Opening the **Behaviors** tab displays dedicated tactical cards for Thrower, Furnace (Firemite spawning/self-decay), Ruin Witch (rubble consumption into Ruin Knights), Super Yeti (Electromite chain lightning), and all 12 Builder Base 2.0 active/passive abilities.
  4. Opening the **Audit Log** highlights newly documented source divergences (e.g., Builder Base 2.0 housing space vs. Army Camp slot scaling, Ruin Witch defensive-only DPS vs. 0 offensive DPS, and Furnace Firemite cap adjustments).
  5. Clicking **Export CSV** or visiting **Raw CSV** outputs RFC 4180 compliant rows preserving all 17 columns including `housing space (troops)`.
- **Visual Identity & Theme**:
  - *Aesthetic Direction*: High-density analytical research console adhering to dark/light dual-theme parity.
  - *Color Palette & Mood*: Deep slate canvas (`#020617`) with elevated structural panels (`#0f172a`), hairline slate borders (`1px`), crisp white/light-mode pair (`#ffffff` / `#f8fafc`), and amber (`#f59e0b`) reserved strictly for active navigation indicators, primary export actions, and housing space highlights.
  - *Typography & Hierarchy*: `Plus Jakarta Sans` for headers, navigation, and prose paired with `JetBrains Mono` (`tabular-nums`) across all numeric columns (Level, TH/BH, HP, DPS, Housing Space, Speed) so values align vertically without jitter.
  - *Component Styling & Layout*: Single-elevation flat containers with 1px hairline borders, clean segmented filter buttons inside the workspace toolbar, single-line controls (`whitespace-nowrap`), and quiet unboxed metadata separators (`·`) instead of decorative pill clusters.
- **Interactive Feedback & Motion**: Instantaneous client-side filtering (<50ms), explicit empty-state messaging with filter reset affordance when search queries match zero rows, and 2-second clipboard copy confirmation feedback.

---

## 3. Key Product Decisions & Trade-Offs

- **Decision 1: Builder Base Housing Space Mapping**
  - *Chosen Approach*: Record the user-specified per-troop Housing Space values directly in the `housingSpace` column (`Sneaky Archer: 3`, `Raged Barbarian: 4`, `Beta Minion: 4`, `Hog Glider: 10`, `Bomber: 12`, `Night Witch: 14`, `Electrofire Wizard: 14`, `Cannon Cart: 16`, `Boxer Giant: 18`, `Baby Dragon: 20`, `Drop Ship: 20`, `Power P.E.K.K.A: 22`) and log how those map against Builder Base 2.0's 1-troop-per-camp-slot / units-per-camp system in the Audit Log.
  - *Why*: Ensures strict parity with the user's requested housing space table while maintaining transparent source provenance.
  - *Alternatives Considered*: Leaving Builder Base housing space as `1` (camp slot) or `0`; rejected because it violates the explicit housing space values provided by the user.

- **Decision 2: Unified Troops Tab with Sub-Category Filter**
  - *Chosen Approach*: Keep the top bar strictly aligned with the established navigation order (`Defenses, Buildings & Traps` -> `Troops` -> `Heroes` -> `Hero Pets` -> `Siege Machines` -> `Behaviors` -> `Audit Log` -> `Raw CSV`) and place the `Elixir | Dark Elixir | Super | Builder Base` selector inside the Troops toolbar.
  - *Why*: Prevents top-bar overcrowding and preserves single-line navigation links at 1440px while making cross-village troop comparison effortless.
  - *Alternatives Considered*: Adding another top-level tab; rejected per Phase 1 user confirmation and Top Bar Contract discipline.

- **Decision 3: Multi-Mode & Non-Standard Combat Stats**
  - *Chosen Approach*: Express dual-mode or indirect-damage troops (such as **Ruin Witch** with `0` offensive DPS / defensive vacuum DPS, **Furnace** with Firemite spawn mechanics, **Cannon Cart** Cannon/Mortar modes, and **Electrofire Wizard** Fire/Electro modes) clearly in `damagePerHit`, `specialAbility`, and `conflictNotes` while keeping numeric base stats clean for sorting and CSV parsing.
  - *Why*: Preserves CSV schema integrity without hiding important tactical mechanics.

---

## 4. Technical Architecture & Data Strategy *(Technical Reference)*

- **Architecture & Component Diagram**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                       Clash Research Workbench                         │
├────────────────────────────────────────────────────────────────────────┤
│ Top Bar: [Wordmark] ── [Ordered Category Tabs] ── [Theme + Export CSV] │
├────────────────────────────────────────────────────────────────────────┤
│ Workspace Toolbar                                                      │
│  ├─ Sub-Filter (Troops Tab): All | Elixir | Dark Elixir | Super | BB   │
│  └─ Selectors: Unit Dropdown + TH/BH Level + Search + Reset            │
├─────────────────────────────┬──────────────────────────────────────────┤
│ Unified Dataset Store       │ Active View Renderer                     │
│  ├─ Elixir (19 w/ Thrower)  │  ├─ 17-Column Tabular Explorer           │
│  ├─ Dark (13 w/ Furnace &   │  │   (includes Housing Space column)     │
│  │    Ruin Witch)           │  ├─ Tactical Behavior Cards              │
│  ├─ Super (17 w/ Super Yeti)│  ├─ Audit Log (Version & Source Diffs)   │
│  └─ Builder Base (12 Troops)│  └─ Raw CSV Preview & RFC 4180 Exporter  │
└─────────────────────────────┴──────────────────────────────────────────┘
```

- **Data Model & State**:
  - Extend the category union type with `'Builder Base Troop'` while keeping `'Home Village' | 'Builder Base' | 'Clan Capital'` in the `village` field.
  - Add full level arrays for **Thrower** (Levels 1–4, TH16–18), **Furnace** (Levels 1–4, TH15–17), **Ruin Witch** (Levels 1–4, TH16–18), **Super Yeti** (Levels 3–8, TH13–18), and all **12 Builder Base Troops** (unlock baseline level up to Level 20, BH2–BH10 / Star Lab 1–10).
  - Add 16 corresponding `TroopBehavior` entries and 4 new `ConflictRecord` audit entries.
- **Interactive Component & State Mapping**:
  - `troopSubCategory` state filters rows inside the `troops` tab (`All`, `Elixir Troop`, `Dark Elixir Troop`, `Super Troop`, `Builder Base Troop`) and dynamically narrows `availableUnitNames` and `thRequired` / BH level options.
  - Switching tabs automatically resets `troopSubCategory` and `selectedUnitName` to `'All'` to avoid stale empty tables.
  - `generateCsvString` reads the active `filteredRows` array so exporting while filtered to `Builder Base Troop` produces a clean Builder Base CSV, while exporting on `All` produces the complete combined roster.
