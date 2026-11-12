# Copy-paste prompts (one per milestone). Always attach/point to AGENTS.md and PROJECT_SPEC.md first.

## Kickoff (first message to any agent)
"Read AGENTS.md and PROJECT_SPEC.md. Run `pip install -r requirements.txt`, `pytest -q`, `python evaluate.py` and summarise the current state in 10 lines. Don't change code yet."

## M1 Data (source: Clash of Clans Fandom wiki)
"Do milestone M1 for Town Hall 8. Run scripts/scrape_fandom.py for: Barbarian, Archer, Giant, Wall Breaker, Goblin, Cannon, Archer Tower, Mortar, Air Defense, Wizard Tower, Town Hall, Gold Storage, Elixir Storage (fix the script if the HTML differs). Raw output goes to data/raw/. Then write scripts/normalize.py that converts raw files into data/troops.json and data/defenses.json in the existing schema, using the level available at TH8 (read the wiki's Town Hall / Laboratory level table, do not guess). Cross-check every troop's HP and DPS against a second source (cocmap.com or coc.guide) and write mismatches into data/DISCREPANCIES.md. Set stats_verified=true only when two sources agree. Add data/SOURCES.md with page URLs and the CC BY-SA attribution note. Movement speed is in wiki 'speed units': keep the raw value and add a documented conversion constant to tiles/second, flagged unverified until calibrated against a real attack recording. Don't invent numbers; list anything missing."

## M2 Bases
"Do M2. Create 5 realistic TH8 layouts in data/bases/ in the existing JSON schema and a validate_base.py. No overlapping footprints, everything inside the 44x44 grid."

## M3 Render
"Do M3. Implement CoCEnv.render() with pygame (rgb_array + human modes), and play_human.py to deploy troops by mouse click. Don't change sim mechanics."

## M4 Walls and pathing
"Do M4: walls (1x1, excluded from destruction %), A* pathfinding, Wall Breaker behaviour, tests."

## M5 Defenses
"Do M5: mortar with min range and splash, air defense, attack delays, flying troops, tests for each mechanic."

## M6 Baselines
"Do M6: three rule-based strategies in agents/, update evaluate.py to run 100 seeded episodes per base per strategy and save results.csv."

## M7 RL
"Do M7: train PPO with sb3-contrib MaskablePPO, action masks for invalid deploys, tensorboard logging, plots, and compare against the M6 baselines on held-out bases. Append every reward change to REWARD_LOG.md."

## M8 Sim-to-real (optional)
"Do M8 as a separate package live/: scrcpy/ADB screenshot capture, OpenCV template matching to detect buildings, convert to base JSON, replay deployments via ADB with small random delays. Keep it isolated from sim/."
