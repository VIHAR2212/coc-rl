import json
from pathlib import Path

exp = json.loads(Path('data/reference/clash_explorer_all.json').read_text(encoding='utf-8'))
targets = {
    'Wizard': 5,
    'Valkyrie': 2,
    'Hog Rider': 4,
    'Golem': 2,
    'Dragon': 3,
    'Balloon': 5,
    'Minion': 4,
}

print('=== CLASH EXPLORER TARGET ROWS ===')
for t in exp:
    name = t.get('name')
    lvl = t.get('level')
    if name in targets and lvl == targets[name] and t.get('village') == 'Home Village':
        print(f"{name} L{lvl} (thReq={t.get('thRequired')}): HP={t.get('hitpoints')}, DPS={t.get('dps')}, speed={t.get('movementSpeed')}, housing={t.get('housingSpace')}")

print('\n=== COC.GUIDE CACHE TARGET ROWS ===')
# Map troop names to cocguide files
cg_files = {
    'Dragon': 'troop_dragon.json',
    'Hog Rider': 'troop_hog-rider.json',
    'Minion': 'troop_minion.json',
    'Valkyrie': 'troop_valkyrie.json',
}
for name, fname in cg_files.items():
    p = Path('data/raw/cocguide_cache') / fname
    if p.exists():
        data = json.loads(p.read_text(encoding='utf-8'))
        tables = data.get('tables', [])
        print(f"\n--- {name} ({fname}) tables: {len(tables)} ---")
        for table in tables:
            for row in table:
                if str(targets[name]) in str(row):
                    print(row)

