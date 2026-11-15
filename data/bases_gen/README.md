# Procedural TH8 Base Layouts (data/bases_gen/)

This directory and its subdirectories contain procedurally generated Town Hall 8 base layouts produced by `sim/base_generator.py` for training and evaluating reinforcement learning agents in Milestone M10.

## Disclaimer & Provenance
> [!NOTE]
> These layouts are **procedural approximations** designed to systematically challenge defensive pathing, wall penetration, core compartment breaches, and target prioritization across diverse geometric archetypes. They are **not real player bases** scraped from the Clash of Clans API, and are not claimed to represent human base-design metagames.

## Layout Specification
- **Grid Dimension:** 44x44 tiles.
- **Rules & Limits:** Strictly conforms to verified Town Hall 8 limits extracted from `data/raw/Town_Hall.json` and `data/defenses.json` (1 Town Hall 4x4, 5 Cannons 3x3, 5 Archer Towers 3x3, 4 Mortars 3x3, 3 Air Defenses 3x3, 3 Wizard Towers 3x3, 1 Bomb Tower 3x3, 3 Hidden Teslas 2x2, 6 Storages 3x3, and $\le 225$ Walls 1x1).
- **Validation:** 100% of generated layouts are validated against `scripts/validate_base.py` ensuring zero footprint overlaps and full bounding-box containment.

## Architectural Styles
1. **`compartmented`**: Concentric rectangular wall enclosures surrounding the Town Hall core with 4 quadrant defensive sub-compartments.
2. **`clustered_core`**: Central high-density fortress with storages and splash defenses enclosed by heavy walls, flanked by a radial outer defensive ring.
3. **`spread_out`**: Widely spaced defense islands with open avenues to deter area splash and chain-pathing.
4. **`defenses_outside`**: Southern-teaser/bait architecture where resource storages and Town Hall occupy a heavily fortified inner core while primary point defenses sit on the outer lawn.
5. **`asymmetric`**: Offset Town Hall positioned along one flank with the primary defensive bastion concentrated on the opposite flank.
6. **`mixed`**: Hybrid layout featuring tight wall compartments on one flank and open funnel lanes with staggered wall teeth on the other.
7. **`open_no_walls`**: Open village layout containing zero walls to isolate raw defense DPS coverage and target pathing.

## Splits
- `data/bases_gen/train/`: 300 procedural layouts generated from seeds 0 to 299.
- `data/bases_gen/heldout_v2/`: 30 procedural layouts generated from seeds 10000 to 10029, filtered to enforce a minimum pairwise distance threshold against all training and legacy layouts. This split is single-use and strictly reserved for final evaluation.
