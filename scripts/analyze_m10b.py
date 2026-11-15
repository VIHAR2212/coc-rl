"""Milestone M10b Analysis:
1. Per-army table on heldout_v2 for left_wave, ppo_m9_bcft_3seed, ppo_m10_bcft_3seed with floor/ceiling flags.
2. Housing space verification against TH8 capacity (200).
3. Paired layout-bootstrap (1,500 resamples) of ppo_m10_bcft_3seed minus ppo_m9_bcft_3seed for dest, stars, 3-star, and TH-kill.
4. Seed spread (max - min) on heldout_v2 for M9 and M10.
"""

import csv
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "results" / "m10_heldout_v2_all_pairs.csv"
ARMIES_PATH = ROOT / "data" / "armies.json"
TROOPS_PATH = ROOT / "data" / "troops.json"

ARMIES = [
    "giant_barch",
    "barch",
    "goblin_giant",
    "mixed_wb",
    "mass_dragons",
    "gowiva",
    "hog_rush",
]

GROUND_ARMIES = ["giant_barch", "barch", "goblin_giant", "mixed_wb"]
NON_DRAGON_ARMIES = [a for a in ARMIES if a != "mass_dragons"]


def step1_per_army_table():
    print("=" * 90)
    print("M10b STEP 1: PER-ARMY TABLE ON HELDOUT_V2 (30 Layouts)")
    print("=" * 90)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    target_agents = ["left_wave", "ppo_m9_bcft_3seed", "ppo_m10_bcft_3seed"]
    
    # Organize data: agent -> army -> list of layout records
    data = {ag: {army: [] for army in ARMIES} for ag in target_agents}
    for r in rows:
        ag = r["agent"]
        army = r["army"]
        if ag in data and army in data[ag]:
            data[ag][army].append(r)

    print(f"{'Army':<15} {'Agent':<20} {'Dest %':<12} {'Stars':<10} {'3-Star %':<15} {'TH-Kill %':<15}")
    print("-" * 90)

    table_data = []

    for army in ARMIES:
        for ag in target_agents:
            recs = data[ag][army]
            m_dest = float(np.mean([float(x["mean_dest"]) for x in recs]))
            m_stars = float(np.mean([float(x["mean_stars"]) for x in recs]))
            m_3star = float(np.mean([float(x["three_star_rate"]) for x in recs]))
            m_th = float(np.mean([float(x["th_kill_rate"]) for x in recs]))

            # Floor / Ceiling checks
            def flag(val, is_pct=True):
                s = f"{val:5.2f}%" if is_pct else f"{val:4.2f}"
                if is_pct:
                    if val <= 0.0001:
                        return f"{s} [FLOOR]"
                    elif val >= 99.9999:
                        return f"{s} [CEILING]"
                return s

            d_str = flag(m_dest, True)
            s_str = flag(m_stars, False)
            ts_str = flag(m_3star, True)
            th_str = flag(m_th, True)

            print(f"{army:<15} {ag:<20} {d_str:<12} {s_str:<10} {ts_str:<15} {th_str:<15}")

            table_data.append({
                "army": army,
                "agent": ag,
                "mean_dest": round(m_dest, 2),
                "mean_stars": round(m_stars, 2),
                "three_star_rate": round(m_3star, 2),
                "th_kill_rate": round(m_th, 2),
                "dest_flag": "FLOOR" if m_dest <= 0.0001 else ("CEILING" if m_dest >= 99.9999 else ""),
                "three_star_flag": "FLOOR" if m_3star <= 0.0001 else ("CEILING" if m_3star >= 99.9999 else ""),
                "th_flag": "FLOOR" if m_th <= 0.0001 else ("CEILING" if m_th >= 99.9999 else ""),
            })
        print("-" * 90)

    # Save table to CSV
    out_csv = ROOT / "results" / "m10b_per_army.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(table_data[0].keys()))
        writer.writeheader()
        writer.writerows(table_data)
    print(f"\nSaved per-army table to {out_csv.name}")

    return table_data


def step2_housing_space():
    print("\n" + "=" * 90)
    print("M10b STEP 2: HOUSING SPACE & TH8 CAPACITY VERIFICATION")
    print("=" * 90)

    with open(ARMIES_PATH, "r", encoding="utf-8") as f:
        armies = json.load(f)
    with open(TROOPS_PATH, "r", encoding="utf-8") as f:
        troops = json.load(f)

    # Wiki data source
    wiki_camp_url = "https://clashofclans.fandom.com/wiki/Army_Camp"
    wiki_th_url = "https://clashofclans.fandom.com/wiki/Town_Hall"
    print(f"TH8 Army Capacity Source: {wiki_camp_url} + {wiki_th_url}")
    print("TH8 Specs: 4 Army Camps at max Level 6 (50 housing space each) = 4 x 50 = 200 total capacity.")
    print("-" * 90)
    print(f"{'Army':<16} {'Composition':<50} {'Housing Space':<15} {'Fills 200 Cap?'}")
    print("-" * 90)

    all_fill = True
    ground_fill = True

    for name, comp in armies.items():
        if name.startswith("_"):
            continue
        total_space = 0
        comp_str_parts = []
        for troop_key, count in comp.items():
            h = troops[troop_key]["housing"]
            total_space += count * h
            comp_str_parts.append(f"{count}x{troops[troop_key]['name']}({h})")
        comp_str = " + ".join(comp_str_parts)
        fills = (total_space == 200)
        if not fills:
            all_fill = False
            if name in GROUND_ARMIES:
                ground_fill = False
        print(f"{name:<16} {comp_str:<50} {total_space:<15} {'YES' if fills else 'NO'}")

    print("-" * 90)
    print(f"Do all 4 original ground armies fill the 200 capacity? {'YES' if ground_fill else 'NO'}")
    print(f"Do all 7 armies fill the 200 capacity? {'YES' if all_fill else 'NO'}")


def step3_paired_bootstrap(n_boot=1500, seed=42):
    print("\n" + "=" * 90)
    print("M10b STEP 3: PAIRED LAYOUT-BOOTSTRAP (ppo_m10_bcft_3seed MINUS ppo_m9_bcft_3seed)")
    print("=" * 90)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Index by agent -> (layout, army) -> metrics
    agents = ["ppo_m10_bcft_3seed", "ppo_m9_bcft_3seed"]
    data = {ag: {} for ag in agents}
    layouts = sorted(list(set(r["base"] for r in rows)))

    for r in rows:
        if r["agent"] in data:
            data[r["agent"]][(r["base"], r["army"])] = {
                "dest": float(r["mean_dest"]),
                "stars": float(r["mean_stars"]),
                "three_star": float(r["three_star_rate"]),
                "th": float(r["th_kill_rate"]),
            }

    subsets = [
        ("All 7 Armies (30 Layouts)", ARMIES),
        ("24 Non-Dragon Armies (30 Layouts)", NON_DRAGON_ARMIES),
        ("4 Ground Armies (30 Layouts)", GROUND_ARMIES),
    ]

    rng = np.random.default_rng(seed)
    n_layouts = len(layouts)

    bootstrap_results = []

    print(f"{'Subset':<32} {'Delta Dest % [95% CI]':<26} {'Delta Stars [95% CI]':<22} {'Delta 3-Star % [95% CI]':<26} {'Delta TH-Kill % [95% CI]'}")
    print("-" * 130)

    for sub_name, army_list in subsets:
        delta_dests = []
        delta_stars = []
        delta_3stars = []
        delta_ths = []

        for _ in range(n_boot):
            sample_layouts = rng.choice(layouts, size=n_layouts, replace=True)

            d_m10, s_m10, ts_m10, th_m10 = [], [], [], []
            d_m9, s_m9, ts_m9, th_m9 = [], [], [], []

            for l in sample_layouts:
                for a in army_list:
                    r10 = data["ppo_m10_bcft_3seed"][(l, a)]
                    r9 = data["ppo_m9_bcft_3seed"][(l, a)]

                    d_m10.append(r10["dest"])
                    s_m10.append(r10["stars"])
                    ts_m10.append(r10["three_star"])
                    th_m10.append(r10["th"])

                    d_m9.append(r9["dest"])
                    s_m9.append(r9["stars"])
                    ts_m9.append(r9["three_star"])
                    th_m9.append(r9["th"])

            delta_dests.append(np.mean(d_m10) - np.mean(d_m9))
            delta_stars.append(np.mean(s_m10) - np.mean(s_m9))
            delta_3stars.append(np.mean(ts_m10) - np.mean(ts_m9))
            delta_ths.append(np.mean(th_m10) - np.mean(th_m9))

        def ci_str(arr, is_pct=True):
            m = float(np.mean(arr))
            lo = float(np.percentile(arr, 2.5))
            hi = float(np.percentile(arr, 97.5))
            if is_pct:
                return f"{m:+5.2f} [{lo:+5.2f}, {hi:+5.2f}]"
            else:
                return f"{m:+5.3f} [{lo:+5.3f}, {hi:+5.3f}]"

        d_s = ci_str(delta_dests, True)
        s_s = ci_str(delta_stars, False)
        ts_s = ci_str(delta_3stars, True)
        th_s = ci_str(delta_ths, True)

        print(f"{sub_name:<32} {d_s:<26} {s_s:<22} {ts_s:<26} {th_s}")

        bootstrap_results.append({
            "subset": sub_name,
            "delta_dest_mean": round(float(np.mean(delta_dests)), 2),
            "delta_dest_ci_lo": round(float(np.percentile(delta_dests, 2.5)), 2),
            "delta_dest_ci_hi": round(float(np.percentile(delta_dests, 97.5)), 2),
            "delta_stars_mean": round(float(np.mean(delta_stars)), 3),
            "delta_stars_ci_lo": round(float(np.percentile(delta_stars, 2.5)), 3),
            "delta_stars_ci_hi": round(float(np.percentile(delta_stars, 97.5)), 3),
            "delta_3star_mean": round(float(np.mean(delta_3stars)), 2),
            "delta_3star_ci_lo": round(float(np.percentile(delta_3stars, 2.5)), 2),
            "delta_3star_ci_hi": round(float(np.percentile(delta_3stars, 97.5)), 2),
            "delta_th_mean": round(float(np.mean(delta_ths)), 2),
            "delta_th_ci_lo": round(float(np.percentile(delta_ths, 2.5)), 2),
            "delta_th_ci_hi": round(float(np.percentile(delta_ths, 97.5)), 2),
        })

    out_csv = ROOT / "results" / "m10b_paired_bootstrap.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(bootstrap_results[0].keys()))
        writer.writeheader()
        writer.writerows(bootstrap_results)
    print(f"\nSaved paired bootstrap results to {out_csv.name}")

    return bootstrap_results


def step4_seed_spread():
    print("\n" + "=" * 90)
    print("M10b STEP 4: SEED SPREAD (MAX - MIN) ON HELDOUT_V2 (SAME 30 LAYOUTS)")
    print("=" * 90)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Agents to inspect: M9 seeds and M10 seeds
    m9_seeds = ["ppo_m9_bcft_seed42", "ppo_m9_bcft_seed43", "ppo_m9_bcft_seed44"]
    m10_seeds = ["ppo_m10_bcft_seed42", "ppo_m10_bcft_seed43", "ppo_m10_bcft_seed44"]

    def get_seed_metrics(seed_list, army_filter=ARMIES):
        metrics = {}
        for s in seed_list:
            recs = [r for r in rows if r["agent"] == s and r["army"] in army_filter]
            metrics[s] = {
                "dest": float(np.mean([float(x["mean_dest"]) for x in recs])),
                "stars": float(np.mean([float(x["mean_stars"]) for x in recs])),
                "three_star": float(np.mean([float(x["three_star_rate"]) for x in recs])),
                "th": float(np.mean([float(x["th_kill_rate"]) for x in recs])),
            }
        return metrics

    for sub_name, a_list in [("All 7 Armies", ARMIES), ("4 Ground Armies", GROUND_ARMIES), ("24 Non-Dragon Armies", NON_DRAGON_ARMIES)]:
        print(f"\n--- {sub_name} (30 Layouts) ---")
        m9_met = get_seed_metrics(m9_seeds, a_list)
        m10_met = get_seed_metrics(m10_seeds, a_list)

        print(f"{'Metric':<18} {'M9 (s42, s43, s44)':<35} {'M9 Spread':<12} {'M10 (s42, s43, s44)':<35} {'M10 Spread'}")
        print("-" * 115)

        for m_key, m_name in [("dest", "Destruction %"), ("stars", "Stars"), ("three_star", "3-Star %"), ("th", "TH-Kill %")]:
            m9_vals = [m9_met[s][m_key] for s in m9_seeds]
            m10_vals = [m10_met[s][m_key] for s in m10_seeds]

            m9_spread = max(m9_vals) - min(m9_vals)
            m10_spread = max(m10_vals) - min(m10_vals)

            if m_key == "stars":
                m9_str = f"{m9_vals[0]:.2f}, {m9_vals[1]:.2f}, {m9_vals[2]:.2f}"
                m10_str = f"{m10_vals[0]:.2f}, {m10_vals[1]:.2f}, {m10_vals[2]:.2f}"
                print(f"{m_name:<18} {m9_str:<35} {m9_spread:5.3f}       {m10_str:<35} {m10_spread:5.3f}")
            else:
                m9_str = f"{m9_vals[0]:.2f}%, {m9_vals[1]:.2f}%, {m9_vals[2]:.2f}%"
                m10_str = f"{m10_vals[0]:.2f}%, {m10_vals[1]:.2f}%, {m10_vals[2]:.2f}%"
                print(f"{m_name:<18} {m9_str:<35} {m9_spread:5.2f} pp    {m10_str:<35} {m10_spread:5.2f} pp")


if __name__ == "__main__":
    step1_per_army_table()
    step2_housing_space()
    step3_paired_bootstrap()
    step4_seed_spread()
