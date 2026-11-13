"""Check TH8 troop levels in sim files vs explorer data."""
import json
from pathlib import Path

DATA_DIR = Path("data")
sim_troops = json.loads((DATA_DIR / "troops.json").read_text(encoding="utf-8"))
explorer = json.loads((DATA_DIR / "reference" / "clash_explorer_all.json").read_text(encoding="utf-8"))

print("=" * 60)
print("TH8 SIMULATOR TROOPS VS EXPLORER DATA")
print("=" * 60)

for k, sim_t in sim_troops.items():
    if k.startswith("_"):
        continue
    name = sim_t["name"]
    sim_lvl = sim_t["level"]
    sim_hp = sim_t["hp"]
    sim_dps = sim_t["dps"]

    exp_rows = [r for r in explorer if r["name"].lower() == name.lower() and r.get("village") == "Home Village"]
    exp_at_sim_lvl = next((r for r in exp_rows if r["level"] == sim_lvl), None)
    
    # What level does explorer say is unlocked at TH8?
    # Filter rows with thRequired <= 8
    exp_at_th8 = [r for r in exp_rows if isinstance(r.get("thRequired"), int) and r.get("thRequired") <= 8]
    max_th8_exp = max(exp_at_th8, key=lambda x: x["level"]) if exp_at_th8 else None

    print(f"\nTroop: {name}")
    print(f"  Simulator TH8: Level {sim_lvl} | HP: {sim_hp} | DPS: {sim_dps}")
    if exp_at_sim_lvl:
        print(f"  Explorer at Lvl {sim_lvl}: TH_req={exp_at_sim_lvl.get('thRequired')} ({exp_at_sim_lvl.get('buildingRequired')}) | HP: {exp_at_sim_lvl.get('hitpoints')} | DPS: {exp_at_sim_lvl.get('dps')}")
    else:
        print(f"  Explorer at Lvl {sim_lvl}: NOT FOUND")
        
    if max_th8_exp:
        print(f"  Explorer Max at TH<=8: Level {max_th8_exp['level']} | TH_req={max_th8_exp.get('thRequired')} ({max_th8_exp.get('buildingRequired')}) | HP: {max_th8_exp.get('hitpoints')} | DPS: {max_th8_exp.get('dps')}")

    # Also list all levels in explorer
    print("  All Explorer Levels:")
    for r in sorted(exp_rows, key=lambda x: x["level"]):
        print(f"    Lvl {r['level']}: TH_req={r.get('thRequired')} ({r.get('buildingRequired')}), HP={r.get('hitpoints')}, DPS={r.get('dps')}")

