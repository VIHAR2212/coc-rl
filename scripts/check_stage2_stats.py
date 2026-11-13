import json
from pathlib import Path

exp = json.loads(Path('data/reference/clash_explorer_all.json').read_text(encoding='utf-8'))
troops = ['Wizard', 'Valkyrie', 'Hog Rider', 'Golem', 'Dragon', 'Balloon', 'Minion']
print('=== CLASH EXPLORER ALL (Home Village) ===')
for t in exp:
    if t.get('name') in troops and t.get('village') == 'Home Village':
        name = t.get('name')
        lvl = t.get('level')
        th = t.get('thRequired')
        hp = t.get('hitpoints')
        dps = t.get('dps')
        speed = t.get('movementSpeed')
        housing = t.get('housingSpace')
        sources = t.get('sources')
        print(f"{name} L{lvl} (thReq={th}): HP={hp}, DPS={dps}, speed={speed}, housing={housing}, sources={sources}")

print('\n=== COC.GUIDE CACHE FILES ===')
for p in Path('data/raw/cocguide_cache').glob('*.json'):
    try:
        content = p.read_text(encoding='utf-8')
        if not content: continue
        data = json.loads(content)
        # Check structure
        print(f"File {p.name}: keys={list(data.keys())[:5]}")
    except Exception as e:
        print(f"Error {p.name}: {e}")
