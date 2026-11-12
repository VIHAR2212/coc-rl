# Data Sources & Attribution (M1)

All Town Hall 8 unit and building stats in `data/troops.json` and `data/defenses.json` were collected via `scripts/scrape_fandom.py` (cached in `data/raw/`) and normalized via `scripts/normalize.py` on 2026-11-12.

## Primary Source: Clash of Clans Wiki (Fandom)

Content from the Clash of Clans Wiki on Fandom is licensed under **Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)** unless otherwise noted (https://clashofclans.fandom.com/wiki/Clash_of_Clans_Wiki:Copyrights).

### Pages scraped (`data/raw/*.json`)
- Barbarian: https://clashofclans.fandom.com/wiki/Barbarian
- Archer: https://clashofclans.fandom.com/wiki/Archer
- Giant: https://clashofclans.fandom.com/wiki/Giant
- Wall Breaker: https://clashofclans.fandom.com/wiki/Wall_Breaker
- Goblin: https://clashofclans.fandom.com/wiki/Goblin
- Cannon: https://clashofclans.fandom.com/wiki/Cannon
- Archer Tower: https://clashofclans.fandom.com/wiki/Archer_Tower
- Mortar: https://clashofclans.fandom.com/wiki/Mortar
- Air Defense: https://clashofclans.fandom.com/wiki/Air_Defense
- Wizard Tower: https://clashofclans.fandom.com/wiki/Wizard_Tower
- Town Hall: https://clashofclans.fandom.com/wiki/Town_Hall
- Gold Storage: https://clashofclans.fandom.com/wiki/Gold_Storage
- Elixir Storage: https://clashofclans.fandom.com/wiki/Elixir_Storage

## Secondary Cross-Check Source: coc.guide

Used via `scripts/scrape_cocguide.py` to cross-check TH8 HP and DPS values (see `data/DISCREPANCIES.md` for mismatches and lag notes):
- Troops: https://coc.guide/troop/barbarian, https://coc.guide/troop/archer, https://coc.guide/troop/giant, https://coc.guide/troop/wall-breaker, https://coc.guide/troop/goblin
- Defenses: https://coc.guide/defense/cannon, https://coc.guide/defense/archer-tower, https://coc.guide/defense/mortar, https://coc.guide/defense/air-defense, https://coc.guide/defense/wizard-tower
- Other / Resources: https://coc.guide/other/town-hall, https://coc.guide/resource/gold-storage, https://coc.guide/resource/elixir-storage

