# coc-rl: Clash of Clans attack simulator + RL agent

Student ML project: Gymnasium simulator of a CoC attack, rule-based baselines, PPO agent.

## Quick start
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest -q
python evaluate.py        # rule-based baseline
python train_ppo.py       # short PPO run (models/ppo_coc_v0)
```

## How to use this with AI Studio / Antigravity / OpenCode
1. Open this folder as the workspace (OpenCode/Antigravity pick up AGENTS.md automatically).
2. For Google AI Studio, paste AGENTS.md + PROJECT_SPEC.md at the start of the chat, then the milestone prompt from PROMPTS.md.
3. Run milestones in order (M1 to M8). Test after each one before moving on.

## IMPORTANT: data is mostly placeholder
Only the Giant L8 stats (hp, dps, attack speed, range, housing, targeting) were read from https://coc.guide/troop/giant. Everything else in `data/*.json` is a placeholder (`stats_verified: false`) so the simulator runs. Do milestone M1 before trusting any result, and never quote simulator numbers on a resume until they come from real data.

## Layout
sim/ (environment), agents/ (baselines), data/ (stats + bases), scripts/ (scraper), tests/, evaluate.py, train_ppo.py

## Data source
Primary: Clash of Clans Fandom wiki via `scripts/scrape_fandom.py` (raw cache in data/raw/). Cross-check with a second site. Fandom text is CC BY-SA, so keep attribution in data/SOURCES.md. coc.guide was found to lag behind the current game (e.g. Giant stops at level 13 there, level 14 exists on Fandom).
