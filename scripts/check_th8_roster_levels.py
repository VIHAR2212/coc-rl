import json

troops = [
    'Barbarian', 'Archer', 'Giant', 'Goblin', 'Wall_Breaker',
    'Balloon', 'Wizard', 'Dragon', 'Minion',
    'Hog_Rider', 'Valkyrie', 'Golem'
]

print("=" * 60)
print("TH8 MAXIMUM TROOP UPGRADE TIERS (LABORATORY LEVEL 6)")
print("=" * 60)

for t in troops:
    filename = f"data/raw/{t}.json"
    raw = json.load(open(filename, encoding='utf-8'))
    max_lvl = 1
    best_row = None
    for table in raw.get('tables', []):
        for r in table:
            lab_req = r.get('Laboratory Level Required')
            if lab_req and lab_req.isdigit() and int(lab_req) <= 6:
                lvl = int(r.get('Level', 0))
                if lvl >= max_lvl:
                    max_lvl = lvl
                    best_row = r
            elif not lab_req and r.get('Level') == '1' and best_row is None:
                best_row = r
    
    # Also check next level requirements to be 100% sure
    next_req = None
    for table in raw.get('tables', []):
        for r in table:
            if r.get('Level') == str(max_lvl + 1):
                next_req = r.get('Laboratory Level Required')

    hp = best_row.get('Hitpoints') if best_row else 'N/A'
    dps = best_row.get('Damage per Second') if best_row else 'N/A'
    print(f"{t:15} | Max Lvl: {max_lvl} (Lab 6) | Next Lvl ({max_lvl+1}) Req: Lab {next_req} | HP: {hp} | DPS: {dps}")

