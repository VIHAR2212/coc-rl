"""Derived M7c numbers used in FINAL_REPORT.txt / REWARD_LOG.md (reads the saved CSVs only).

Prints:
  - per-army breakdown for the key agents
  - paired Part B - ablation deltas with bootstrap CIs
  - paired PPO vs left_wave on the 16 ground-army pairs
  - Part A's stored 16-pair numbers (old simulator)
  - action diagnostics by model group
  - reproduction check of Part B's baseline rows on the 16 shared pairs
"""
import csv
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, "scripts")
from evaluate_m7b_partB import bootstrap_ci  # noqa: E402

BASES = ["base07.json", "base08.json", "base09.json", "base10.json"]
GROUND = ["giant_barch", "barch", "goblin_giant", "mixed_wb"]
ARMIES = GROUND + ["mass_dragons", "gowiva", "hog_rush"]

rows = list(csv.DictReader(open("results/m7c_all_armies.csv")))
by = defaultdict(dict)
for r in rows:
    by[r["agent"]][(r["base"], r["army"])] = r

agents = ["left_wave", "maskable_ppo_partB_3seed", "maskable_ppo_noac_3seed", "random_masked"]
print("PER-ARMY (mean over 4 bases): destruction % / stars / 3-star %")
print(f"{'army':<14}" + "".join(f"{a[:24]:>26}" for a in agents))
for a in ARMIES:
    line = f"{a:<14}"
    for ag in agents:
        rs = [r for (b, aa), r in by[ag].items() if aa == a]
        line += (f"{np.mean([float(x['mean_dest_pct']) for x in rs]):8.2f}"
                 f"{np.mean([float(x['mean_stars']) for x in rs]):7.2f}"
                 f"{np.mean([float(x['three_star_pct']) for x in rs]):7.1f}")
    print(line)

print("\nPaired Part B(3seed) - ablation(3seed) over 28 pairs (bootstrap 95% CI):")
for name, key in [("dest", "mean_dest_pct"), ("stars", "mean_stars"), ("3star", "three_star_pct")]:
    d = [float(by["maskable_ppo_partB_3seed"][k][key]) - float(by["maskable_ppo_noac_3seed"][k][key])
         for k in sorted(by["maskable_ppo_partB_3seed"])]
    m, lo, hi = bootstrap_ci(d)
    print(f"  {name:6s} {m:+7.3f} [{lo:+7.3f}, {hi:+7.3f}]")

print("\nPaired PPO/random vs left_wave on the 16 ground-army pairs (same simulator):")
for ag in ["maskable_ppo_partB_3seed", "maskable_ppo_noac_3seed", "random_masked"]:
    for name, key in [("dest", "mean_dest_pct"), ("stars", "mean_stars"), ("3star", "three_star_pct")]:
        d = [float(by[ag][(b, a)][key]) - float(by["left_wave"][(b, a)][key]) for b in BASES for a in GROUND]
        m, lo, hi = bootstrap_ci(d)
        print(f"  {ag:<28} {name:6s} {m:+7.3f} [{lo:+7.3f}, {hi:+7.3f}]")

print("\nPart A stored results (16 pairs, pre-Stage-2 simulator - not re-runnable):")
pa = list(csv.DictReader(open("results/m7b_partA.csv")))
for ag in ["left_wave", "maskable_ppo", "random_masked"]:
    sub = [r for r in pa if r["agent"] == ag]
    print(f"  {ag:<14} dest {np.mean([float(r['mean_dest_pct']) for r in sub]):6.2f} "
          f"stars {np.mean([float(r['mean_stars']) for r in sub]):5.2f} "
          f"3star {np.mean([float(r['three_star_pct']) for r in sub]):6.2f}")

print("\nAction diagnostics by model group (from results/m7c_action_diagnostics.csv):")
diag = list(csv.DictReader(open("results/m7c_action_diagnostics.csv")))
for grp, pref in [("Part B", "ppo_m7b_seed"), ("Ablation", "ppo_m7c_noac_seed")]:
    sel = [r for r in diag if r["model_file"].startswith(pref)]
    sec = [float(r["avg_distinct_sectors_per_ep"]) for r in sel]
    ent = [float(r["action_entropy"]) for r in sel]
    collapse = sum(float(r["single_sector_fraction"]) > 0.9 for r in sel)
    print(f"  {grp:<9} n={len(sel)} sectors {np.mean(sec):.2f} [{min(sec):.2f},{max(sec):.2f}] "
          f"entropy {np.mean(ent):.2f} [{min(ent):.2f},{max(ent):.2f}] collapse {collapse}")

print("\nReproduction check: Part B baseline rows vs the M7c sweep on the 16 shared pairs")
partb = {(r["agent"], r["base"], r["army"]): r for r in csv.DictReader(open("results/m7b_partB.csv"))}
worst = 0.0
checked = 0
for ag in ["left_wave", "surround", "smart_funnel", "random_masked"]:
    for b in BASES:
        for a in GROUND:
            new, old = by[ag][(b, a)], partb[(ag, b, a)]
            worst = max(worst, max(abs(float(new[k]) - float(old[k]))
                                   for k in ("mean_dest_pct", "mean_stars", "three_star_pct")))
            checked += 1
print(f"  {checked} agent-pair rows compared, max |delta| = {worst:.6f}")