import json

for name in ['Giant', 'Barbarian', 'Archer', 'Wall_Breaker', 'Goblin']:
    raw = json.load(open(f'data/raw/{name}.json', encoding='utf-8'))
    print(f'=== {name} ===')
    for t in raw.get('tables', []):
        for r in t:
            if r.get('Level') in ['4', '5', '6', '7']:
                print(f"  Level {r['Level']}: Lab Req = {r.get('Laboratory Level Required')} | HP = {r.get('Hitpoints')} | DPS = {r.get('Damage per Second')}")
