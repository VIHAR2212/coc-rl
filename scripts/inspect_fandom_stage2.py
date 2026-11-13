import json
from pathlib import Path

raw_troops = {
    'Wizard': ('Wizard.json', '5'),
    'Valkyrie': ('Valkyrie.json', '2'),
    'Hog Rider': ('Hog_Rider.json', '4'),
    'Golem': ('Golem.json', '2'),
    'Dragon': ('Dragon.json', '3'),
    'Balloon': ('Balloon.json', '5'),
    'Minion': ('Minion.json', '4'),
}

for name, (fname, lvl) in raw_troops.items():
    p = Path('data/raw') / fname
    data = json.loads(p.read_text(encoding='utf-8'))
    print(f"\n==================== {name} (L{lvl}) ====================")
    if 'tables' in data and data['tables']:
        # Table 0: stats/infobox
        print("Infobox / Table 0:", data['tables'][0])
        # Find upgrade table
        for t in data['tables'][1:]:
            for row in t:
                if isinstance(row, dict) and row.get('Level') == lvl:
                    print(f"Upgrade Level {lvl}:", row)

