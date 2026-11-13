import json
from pathlib import Path

raw_troops = {
    'Wizard': ('Wizard.json', 5),
    'Valkyrie': ('Valkyrie.json', 2),
    'Hog_Rider': ('Hog_Rider.json', 4),
    'Golem': ('Golem.json', 2),
    'Dragon': ('Dragon.json', 3),
    'Balloon': ('Balloon.json', 5),
    'Minion': ('Minion.json', 4),
}

for name, (fname, lvl) in raw_troops.items():
    p = Path('data/raw') / fname
    data = json.loads(p.read_text(encoding='utf-8'))
    print(f"=== {name} (L{lvl}) ===")
    tables = data.get('tables', [])
    for t_idx, t in enumerate(tables):
        for row in t:
            if row and (row[0] == str(lvl) or str(lvl) in row[:2]):
                print(f"Table {t_idx} row: {row}")

