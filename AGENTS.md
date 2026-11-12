# AGENTS.md: rules for any AI coding agent working in this repo
(OpenCode and Antigravity read this file automatically. In Google AI Studio, paste it together with PROJECT_SPEC.md.)

Project: Clash of Clans attack simulator + RL agent (student ML project). Read PROJECT_SPEC.md first.

Rules
1. Work on ONE milestone at a time (see PROJECT_SPEC.md). After each, run `pytest -q` and `python evaluate.py`.
2. Never hardcode unit stats in code. All stats live in data/*.json. Entries with `stats_verified: false` are placeholders; never present them as real numbers.
3. The sim must stay deterministic given a seed. No wall-clock time, no unseeded randomness.
4. Keep the Gymnasium API valid (reset/step/spaces). Run `stable_baselines3.common.env_checker.check_env` after changing the env.
5. Don't rewrite files the milestone doesn't need. Small diffs, explain what changed.
6. Log every reward-design change and why in `REWARD_LOG.md` (what was tried, what broke). This is interview material.
7. Never invent wiki numbers. If a stat is missing, add a TODO and ask the human.
8. Don't add features outside the current milestone.
