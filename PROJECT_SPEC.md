# PROJECT_SPEC: Clash of Clans Attack Simulator + RL Agent

## Goal
A faithful-as-practical simulator of a CoC home-village attack at ONE Town Hall level (TH7 or TH8), a rule-based baseline attacker, and an RL agent (PPO) that learns troop deployment. Report destruction % and stars vs the baseline. Optional last stage: replay on a real emulator.

Supercell's engine is closed source. This is an approximation built from public wiki data (https://coc.guide, the CoC wiki). Be explicit about every simplification.

## Current state (starter already runs)
- `sim/env.py`: Gymnasium env, grid 44x44, straight-line troop movement, defenses with continuous dps, destruction %, TH bonus.
- 3 troops, 4 building types, 1 sample base, all with PLACEHOLDER stats except Giant L8 (verified from coc.guide).
- `agents/rule_based.py`, `evaluate.py`, `train_ppo.py`, `tests/test_env.py`.
- Known issue: with placeholder stats the sample base is too easy (baseline gets 100%). Fix with real stats + a realistic base (M1/M2).

## Real mechanics to model (priority order)
1. Real stats per level: HP, DPS, attack speed, range, movement speed, housing, targeting (ground/air), favorite target.
2. Building footprints, no-deploy zone around buildings, 44x44 playable grid, 3-minute battle (180 s), stars: 50% = 1, Town Hall = 1, 100% = 1. Walls do not count toward destruction %.
3. Walls and pathfinding (A* around walls; troops attack walls when no path; Wall Breakers target walls).
4. Defense specifics: Cannon (ground), Archer Tower (air+ground), Mortar (splash, min range), Air Defense, Wizard Tower (splash), Mortar min range, attack speed + projectile delay.
5. Troop targeting rules: Giant -> defenses, Goblin -> resources, Wall Breaker -> walls, others -> nearest building; retarget when target dies.
6. Splash damage, flying vs ground, Hidden traps (bomb, spring), Clan Castle troops, spells (Lightning, Rage, Heal, Freeze), Heroes.

## Milestones (acceptance criteria)
- M1 DATA: fill data/troops.json + data/defenses.json with real values for the chosen TH level (use scripts/scrape_cocguide.py; movement speed from another source). Set `stats_verified: true` only for values checked against a source. Add `data/SOURCES.md`.
- M2 BASES: add 5+ realistic base layouts in data/bases/ (can be hand-made from public TH base layouts). Provide `scripts/validate_base.py` (no overlaps, inside the grid).
- M3 RENDER: pygame/matplotlib `render()`; `play_human.py` where a human can click to deploy. Verify behavior by eye.
- M4 WALLS+PATHING: walls as 1x1 buildings, A* pathing, Wall Breaker. Tests for pathing.
- M5 DEFENSE REALISM: mortar, air defense, splash, attack delays, flying troops (Minion/Balloon). Unit tests per mechanic.
- M6 BASELINES: at least 3 rule-based strategies; `evaluate.py` prints destruction %, stars, 3-star rate over 100 seeded episodes per base; save CSV.
- M7 RL: PPO (SB3). Train on one base, then randomized bases. Action masking (sb3-contrib MaskablePPO) for invalid deploys. Plot reward curves, compare vs baselines, ablations of reward terms. Record in REWARD_LOG.md.
- M8 SIM-TO-REAL (optional, last): emulator + ADB + OpenCV (template matching or YOLO) to read a real base into a base JSON, and replay agent deployments. Use a throwaway account, short sessions only. Report the gap between sim and real results.

## Resume-grade deliverables
README with architecture diagram, results table (agent vs baselines), reward-curve plots, 1-2 demo GIFs, REWARD_LOG.md (what failed and why), honest limitations list.

## Non-goals
Full fidelity across all Town Halls; matching Supercell's exact internal formulas; online matchmaking.
