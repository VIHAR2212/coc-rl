"""Final M9 Evaluation on all 28 held-out pairs (base07..base10 x 7 armies).

M9 Step 4:
- Evaluates:
  1. left_wave baseline
  2. Part B MaskablePPO (seeds 42, 43, 44, and 3-seed aggregate)
  3. BC-only (seeds 42, 43, 44, and 3-seed aggregate)
  4. BC + PPO fine-tuned (seeds 42, 43, 44, and 3-seed aggregate)
- Evaluated on all 28 held-out pairs with seeds 0..99 (100 episodes per pair).
- Metrics:
  - Mean destruction %
  - Mean stars
  - 3-star rate %
  - Town Hall kill rate %
  - >=50% destruction rate %
  - Paired bootstrap 95% confidence intervals against left_wave.
- Reports breakdowns across:
  - All 28 pairs
  - 4 original ground armies (giant_barch, barch, goblin_giant, mixed_wb)
  - 24 non-dragon pairs (all 6 non-dragon armies)
- Computes per-seed variance table (Part B vs BC vs BC+PPO).
- Saves results to results/m9_all_pairs.csv and results/m9_summary.csv.
"""

import csv
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["PYTHONPATH"] = str(ROOT)

from agents.rule_based import rule_based_action
from sim import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv

HELD_OUT_BASES = ["base07.json", "base08.json", "base09.json", "base10.json"]
DEFAULT_ARMIES = [
    "giant_barch",
    "barch",
    "goblin_giant",
    "mixed_wb",
    "mass_dragons",
    "gowiva",
    "hog_rush",
]
GROUND_ARMIES_4 = ["giant_barch", "barch", "goblin_giant", "mixed_wb"]
NON_DRAGON_ARMIES_6 = [a for a in DEFAULT_ARMIES if a != "mass_dragons"]

EPISODES_PER_PAIR = 100
SEEDS = [42, 43, 44]
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "agent",
    "base",
    "army",
    "episodes",
    "mean_dest_pct",
    "std_dest_pct",
    "min_dest_pct",
    "max_dest_pct",
    "mean_stars",
    "three_star_pct",
    "th_kill_pct",
    "cross_50_pct",
]


def bootstrap_ci(values: list[float], n_boot: int = 10000, seed: int = 42) -> tuple[float, float, float]:
    arr = np.array(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(arr)
    indices = rng.integers(0, n, size=(n_boot, n))
    samples = arr[indices]
    boot_means = np.mean(samples, axis=1)
    lo = float(np.percentile(boot_means, 2.5))
    hi = float(np.percentile(boot_means, 97.5))
    mean = float(np.mean(arr))
    return mean, lo, hi


def _eval_left_wave_pair(args):
    base_file, army_name, episodes = args
    env = CoCEnv(base_file=base_file, army=army_name)
    dests, stars, three_stars, th_kills, cross_50s = [], [], [], [], []

    for ep in range(episodes):
        env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}
        while not done:
            action = rule_based_action(env, step_idx)
            _, _, term, trunc, info = env.step(action)
            done = term or trunc
            step_idx += 1

        d = float(info["destruction"])
        s = int(info["stars"])
        th_hit = bool(env.th_destroyed)

        dests.append(d)
        stars.append(s)
        three_stars.append(int(s == 3))
        th_kills.append(int(th_hit))
        cross_50s.append(int(d >= 0.50))

    return {
        "agent": "left_wave",
        "base": base_file,
        "army": army_name,
        "episodes": episodes,
        "mean_dest_pct": round(float(np.mean(dests)) * 100.0, 4),
        "std_dest_pct": round(float(np.std(dests)) * 100.0, 4),
        "min_dest_pct": round(float(np.min(dests)) * 100.0, 4),
        "max_dest_pct": round(float(np.max(dests)) * 100.0, 4),
        "mean_stars": round(float(np.mean(stars)), 4),
        "three_star_pct": round(float(np.mean(three_stars)) * 100.0, 4),
        "th_kill_pct": round(float(np.mean(th_kills)) * 100.0, 4),
        "cross_50_pct": round(float(np.mean(cross_50s)) * 100.0, 4),
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_3stars": three_stars,
        "raw_th": th_kills,
        "raw_c50": cross_50s,
    }


def _eval_model_pair(args):
    agent_label, model_path_str, base_file, army_name, episodes = args
    from sb3_contrib import MaskablePPO

    model_path = Path(model_path_str)
    model = MaskablePPO.load(model_path, device="cpu")
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army_name], shaping_mode="stars_aware")

    dests, stars, three_stars, th_kills, cross_50s = [], [], [], [], []

    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}

        while not done:
            mask = env.action_masks()
            act, _ = model.predict(obs, action_masks=mask, deterministic=True)
            obs, _, term, trunc, info = env.step(int(act))
            done = term or trunc
            step_idx += 1

        d = float(info["destruction"])
        s = int(info["stars"])
        th_hit = bool(env.env.th_destroyed)

        dests.append(d)
        stars.append(s)
        three_stars.append(int(s == 3))
        th_kills.append(int(th_hit))
        cross_50s.append(int(d >= 0.50))

    return {
        "agent": agent_label,
        "base": base_file,
        "army": army_name,
        "episodes": episodes,
        "mean_dest_pct": round(float(np.mean(dests)) * 100.0, 4),
        "std_dest_pct": round(float(np.std(dests)) * 100.0, 4),
        "min_dest_pct": round(float(np.min(dests)) * 100.0, 4),
        "max_dest_pct": round(float(np.max(dests)) * 100.0, 4),
        "mean_stars": round(float(np.mean(stars)), 4),
        "three_star_pct": round(float(np.mean(three_stars)) * 100.0, 4),
        "th_kill_pct": round(float(np.mean(th_kills)) * 100.0, 4),
        "cross_50_pct": round(float(np.mean(cross_50s)) * 100.0, 4),
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_3stars": three_stars,
        "raw_th": th_kills,
        "raw_c50": cross_50s,
    }


def _condense_seed_rows(rows: list[dict], agg_label: str) -> dict:
    dests = [d for r in rows for d in r["raw_dests"]]
    stars = [s for r in rows for s in r["raw_stars"]]
    three = [t for r in rows for t in r["raw_3stars"]]
    th = [h for r in rows for h in r["raw_th"]]
    c50 = [c for r in rows for c in r["raw_c50"]]
    return {
        "agent": agg_label,
        "base": rows[0]["base"],
        "army": rows[0]["army"],
        "episodes": len(dests),
        "mean_dest_pct": round(float(np.mean(dests)) * 100.0, 4),
        "std_dest_pct": round(float(np.std(dests)) * 100.0, 4),
        "min_dest_pct": round(float(np.min(dests)) * 100.0, 4),
        "max_dest_pct": round(float(np.max(dests)) * 100.0, 4),
        "mean_stars": round(float(np.mean(stars)), 4),
        "three_star_pct": round(float(np.mean(three)) * 100.0, 4),
        "th_kill_pct": round(float(np.mean(th)) * 100.0, 4),
        "cross_50_pct": round(float(np.mean(c50)) * 100.0, 4),
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_3stars": three,
        "raw_th": th,
        "raw_c50": c50,
    }


def compute_subset_metrics(all_rows: list[dict], agent_names: list[str], pair_subset: list[tuple[str, str]], subset_name: str, lw_by_pair: dict):
    print("\n" + "=" * 124)
    print(f"SUBSET: {subset_name} ({len(pair_subset)} pairs, {len(pair_subset)*100} episodes per agent)")
    print("=" * 124)
    print(
        f"{'Agent':<28} {'Dest % [95% CI]':<22} {'Stars [95% CI]':<18} "
        f"{'3-Star %':<10} {'TH-Kill %':<11} {'>=50% %':<10} {'dDest vs LW [95% CI]':<22} {'dStars vs LW [95% CI]':<20}"
    )
    print("-" * 124)

    results = []
    subset_set = set(pair_subset)

    for name in agent_names:
        rows = [r for r in all_rows if r["agent"] == name and (r["base"], r["army"]) in subset_set]
        assert len(rows) == len(pair_subset), f"{name}: expected {len(pair_subset)} rows, got {len(rows)}"

        d = [r["mean_dest_pct"] for r in rows]
        s = [r["mean_stars"] for r in rows]
        t = [r["three_star_pct"] for r in rows]
        th = [r["th_kill_pct"] for r in rows]
        c = [r["cross_50_pct"] for r in rows]

        dm, dlo, dhi = bootstrap_ci(d)
        sm, slo, shi = bootstrap_ci(s)
        tm = float(np.mean(t))
        thm = float(np.mean(th))
        cm = float(np.mean(c))

        if name == "left_wave":
            ddm, ddlo, ddhi = 0.0, 0.0, 0.0
            dsm, dslo, dshi = 0.0, 0.0, 0.0
        else:
            pair_dd = [r["mean_dest_pct"] - lw_by_pair[(r["base"], r["army"])]["mean_dest_pct"] for r in rows]
            pair_ds = [r["mean_stars"] - lw_by_pair[(r["base"], r["army"])]["mean_stars"] for r in rows]
            ddm, ddlo, ddhi = bootstrap_ci(pair_dd)
            dsm, dslo, dshi = bootstrap_ci(pair_ds)

        dest_str = f"{dm:5.2f}% [{dlo:5.2f}, {dhi:5.2f}]"
        star_str = f"{sm:4.2f} [{slo:4.2f}, {shi:4.2f}]"
        dd_str = f"{ddm:+5.2f}% [{ddlo:+5.2f}, {ddhi:+5.2f}]" if name != "left_wave" else "-"
        ds_str = f"{dsm:+4.2f} [{dslo:+4.2f}, {dshi:+4.2f}]" if name != "left_wave" else "-"

        print(
            f"{name:<28} {dest_str:<22} {star_str:<18} {tm:5.1f}%     {thm:5.1f}%      {cm:5.1f}%     {dd_str:<22} {ds_str:<20}"
        )

        results.append({
            "subset": subset_name,
            "agent": name,
            "mean_dest_pct": round(dm, 2),
            "dest_ci_lo": round(dlo, 2),
            "dest_ci_hi": round(dhi, 2),
            "mean_stars": round(sm, 2),
            "stars_ci_lo": round(slo, 2),
            "stars_ci_hi": round(shi, 2),
            "three_star_pct": round(tm, 2),
            "th_kill_pct": round(thm, 2),
            "cross_50_pct": round(cm, 2),
            "delta_dest_vs_lw": round(ddm, 2),
            "delta_dest_ci_lo": round(ddlo, 2),
            "delta_dest_ci_hi": round(ddhi, 2),
            "delta_stars_vs_lw": round(dsm, 2),
            "delta_stars_ci_lo": round(dslo, 2),
            "delta_stars_ci_hi": round(dshi, 2),
        })
    return results


def main(workers: int = 2):
    t0 = time.perf_counter()
    pairs = [(b, a) for b in HELD_OUT_BASES for a in DEFAULT_ARMIES]

    print("=" * 80)
    print("M9 STEP 4: FINAL EVALUATION ON 28 HELD-OUT PAIRS")
    print(f"Bases: {HELD_OUT_BASES}")
    print(f"Armies: {DEFAULT_ARMIES}")
    print(f"Total pairs: {len(pairs)} | Episodes per pair: {EPISODES_PER_PAIR} | Workers: {workers}")
    print("=" * 80, flush=True)

    # 1. Evaluate left_wave (or load from results/m9_bc.csv if available)
    lw_rows = []
    bc_cache_path = RESULTS_DIR / "m9_bc.csv"
    if bc_cache_path.exists():
        with bc_cache_path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["agent"] == "left_wave":
                    lw_rows.append({
                        "agent": "left_wave",
                        "base": row["base"],
                        "army": row["army"],
                        "episodes": int(row["episodes"]),
                        "mean_dest_pct": float(row["mean_dest_pct"]),
                        "std_dest_pct": float(row["std_dest_pct"]),
                        "min_dest_pct": float(row["min_dest_pct"]),
                        "max_dest_pct": float(row["max_dest_pct"]),
                        "mean_stars": float(row["mean_stars"]),
                        "three_star_pct": float(row["three_star_pct"]),
                        "th_kill_pct": float(row["th_kill_pct"]),
                        "cross_50_pct": float(row["cross_50_pct"]),
                    })
    if len(lw_rows) == len(pairs):
        print(f"Loaded all {len(lw_rows)} left_wave results from {bc_cache_path.name}", flush=True)
    else:
        lw_tasks = [(b, a, EPISODES_PER_PAIR) for b, a in pairs]
        print(f"\n--- 1. Evaluating left_wave ({len(lw_tasks)} tasks) ---", flush=True)
        lw_rows = []
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for idx, res in enumerate(pool.map(_eval_left_wave_pair, lw_tasks), 1):
                lw_rows.append(res)
                if idx % 7 == 0 or idx == len(lw_tasks):
                    print(f"  [{idx}/{len(lw_tasks)}] left_wave | {res['base']} | {res['army']} ({time.perf_counter() - t0:.1f}s)", flush=True)

    lw_by_pair = {(r["base"], r["army"]): r for r in lw_rows}

    # Model evaluation definitions
    # Load BC models from cache if present
    bc_cached_rows = []
    if bc_cache_path.exists():
        with bc_cache_path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for s in SEEDS:
                    if row["agent"] == f"ppo_m9_bc_seed{s}_det":
                        bc_cached_rows.append({
                            "agent": f"ppo_m9_bc_seed{s}",
                            "base": row["base"],
                            "army": row["army"],
                            "episodes": int(row["episodes"]),
                            "mean_dest_pct": float(row["mean_dest_pct"]),
                            "std_dest_pct": float(row["std_dest_pct"]),
                            "min_dest_pct": float(row["min_dest_pct"]),
                            "max_dest_pct": float(row["max_dest_pct"]),
                            "mean_stars": float(row["mean_stars"]),
                            "three_star_pct": float(row["three_star_pct"]),
                            "th_kill_pct": float(row["th_kill_pct"]),
                            "cross_50_pct": float(row["cross_50_pct"]),
                        })
                if row["agent"] == "ppo_m9_bc_3seed_det":
                    bc_cached_rows.append({
                        "agent": "ppo_m9_bc_3seed",
                        "base": row["base"],
                        "army": row["army"],
                        "episodes": int(row["episodes"]),
                        "mean_dest_pct": float(row["mean_dest_pct"]),
                        "std_dest_pct": float(row["std_dest_pct"]),
                        "min_dest_pct": float(row["min_dest_pct"]),
                        "max_dest_pct": float(row["max_dest_pct"]),
                        "mean_stars": float(row["mean_stars"]),
                        "three_star_pct": float(row["three_star_pct"]),
                        "th_kill_pct": float(row["th_kill_pct"]),
                        "cross_50_pct": float(row["cross_50_pct"]),
                    })

    model_groups = {
        "Part B PPO": [
            ("maskable_ppo_partB_seed42", ROOT / "models" / "ppo_m7b_seed42.zip"),
            ("maskable_ppo_partB_seed43", ROOT / "models" / "ppo_m7b_seed43.zip"),
            ("maskable_ppo_partB_seed44", ROOT / "models" / "ppo_m7b_seed44.zip"),
        ],
        "BC + PPO Fine-Tuned": [
            ("ppo_m9_bcft_seed42", ROOT / "models" / "ppo_m9_bcft_seed42.zip"),
            ("ppo_m9_bcft_seed43", ROOT / "models" / "ppo_m9_bcft_seed43.zip"),
            ("ppo_m9_bcft_seed44", ROOT / "models" / "ppo_m9_bcft_seed44.zip"),
        ],
    }

    model_tasks = []
    for grp_name, m_list in model_groups.items():
        for label, m_path in m_list:
            if not m_path.exists():
                raise FileNotFoundError(f"Model {m_path} not found!")
            for b, a in pairs:
                model_tasks.append((label, str(m_path), b, a, EPISODES_PER_PAIR))

    print(f"\n--- 2. Evaluating RL & BC Policies ({len(model_tasks)} tasks) ---", flush=True)
    model_rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_model_pair, model_tasks), 1):
            model_rows.append(res)
            if idx % 28 == 0 or idx == len(model_tasks):
                print(f"  [{idx}/{len(model_tasks)}] {res['agent']} | {res['base']} | {res['army']} ({time.perf_counter() - t0:.1f}s)", flush=True)

    # 3. Construct 3-seed aggregates for Part B and Fine-Tuned PPO
    agg_rows = []
    for grp_label, agg_label in [
        ("maskable_ppo_partB", "maskable_ppo_partB_3seed"),
        ("ppo_m9_bcft", "ppo_m9_bcft_3seed"),
    ]:
        for b, a in pairs:
            seed_rows = [r for r in model_rows if r["agent"].startswith(grp_label) and r["base"] == b and r["army"] == a]
            agg_rows.append(_condense_seed_rows(seed_rows, agg_label))

    all_rows = lw_rows + bc_cached_rows + model_rows + agg_rows

    # Save full per-pair records
    all_pairs_csv = RESULTS_DIR / "m9_all_pairs.csv"
    with all_pairs_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in all_rows:
            writer.writerow({k: r[k] for k in FIELDS})
    print(f"\nSaved full per-pair dataset to {all_pairs_csv}", flush=True)

    # Agent order for reporting
    agent_names = [
        "left_wave",
        "maskable_ppo_partB_seed42",
        "maskable_ppo_partB_seed43",
        "maskable_ppo_partB_seed44",
        "maskable_ppo_partB_3seed",
        "ppo_m9_bc_seed42",
        "ppo_m9_bc_seed43",
        "ppo_m9_bc_seed44",
        "ppo_m9_bc_3seed",
        "ppo_m9_bcft_seed42",
        "ppo_m9_bcft_seed43",
        "ppo_m9_bcft_seed44",
        "ppo_m9_bcft_3seed",
    ]

    all_summary_rows = []

    # Subset 1: All 28 pairs
    sum_all = compute_subset_metrics(all_rows, agent_names, pairs, "All 28 Pairs", lw_by_pair)
    all_summary_rows.extend(sum_all)

    # Subset 2: 4 Original Ground Armies
    ground_pairs = [(b, a) for b in HELD_OUT_BASES for a in GROUND_ARMIES_4]
    sum_ground = compute_subset_metrics(all_rows, agent_names, ground_pairs, "4 Ground Armies", lw_by_pair)
    all_summary_rows.extend(sum_ground)

    # Subset 3: 24 Non-Dragon Pairs
    non_dragon_pairs = [(b, a) for b in HELD_OUT_BASES for a in NON_DRAGON_ARMIES_6]
    sum_non_drag = compute_subset_metrics(all_rows, agent_names, non_dragon_pairs, "24 Non-Dragon Pairs", lw_by_pair)
    all_summary_rows.extend(sum_non_drag)

    # Subset 4: Per Army Breakdowns (4 held-out bases per army)
    for a in DEFAULT_ARMIES:
        a_pairs = [(b, a) for b in HELD_OUT_BASES]
        sum_a = compute_subset_metrics(all_rows, agent_names, a_pairs, f"Army: {a}", lw_by_pair)
        all_summary_rows.extend(sum_a)

    # Save summary CSV
    summary_csv = RESULTS_DIR / "m9_summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        sum_fields = list(all_summary_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=sum_fields)
        writer.writeheader()
        writer.writerows(all_summary_rows)
    print(f"\nSaved summary tables to {summary_csv}", flush=True)

    # 4. Per-seed Variance Analysis
    print("\n" + "=" * 90)
    print("M9 SEED-TO-SEED VARIANCE COMPARISON (Mean Destruction % across 28 pairs)")
    print("=" * 90)
    print(f"{'Method':<24} {'Seed 42':<12} {'Seed 43':<12} {'Seed 44':<12} {'Mean':<10} {'StdDev':<10}")
    print("-" * 90)

    for prefix, method_name in [
        ("maskable_ppo_partB", "Part B PPO (from scratch)"),
        ("ppo_m9_bc", "BC-Only"),
        ("ppo_m9_bcft", "BC + PPO Fine-Tuned"),
    ]:
        s_dests = []
        for s in SEEDS:
            agent = f"{prefix}_seed{s}"
            r_list = [r["mean_dest_pct"] for r in all_rows if r["agent"] == agent]
            s_dests.append(float(np.mean(r_list)))
        m_val = float(np.mean(s_dests))
        std_val = float(np.std(s_dests, ddof=1))
        print(
            f"{method_name:<24} {s_dests[0]:<12.2f} {s_dests[1]:<12.2f} {s_dests[2]:<12.2f} {m_val:<10.2f} {std_val:<10.2f}"
        )
    print("=" * 90, flush=True)


if __name__ == "__main__":
    main()

