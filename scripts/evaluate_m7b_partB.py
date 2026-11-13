"""Evaluate M7b Part B: held-out bases 07-10 across all baselines and 3-seed MaskablePPO.
Computes bootstrap 95% confidence intervals, paired deltas, and PPO action diagnostics.
Saves results to results/m7b_partB.csv and results/ppo_action_diagnostics_partB.csv.
"""
import csv
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["PYTHONPATH"] = str(ROOT)

from agents import STRATEGIES
from sim import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv, NUM_SECTORS

HELD_OUT_BASES = ["base07.json", "base08.json", "base09.json", "base10.json"]
ARMIES = ["giant_barch", "barch", "goblin_giant", "mixed_wb"]
EPISODES_PER_PAIR = 100
PPO_SEEDS = [42, 43, 44]


def _eval_baseline_pair(args):
    strategy_name, base_file, army_name, episodes = args
    policy_fn = STRATEGIES[strategy_name]
    env = CoCEnv(base_file=base_file, army=army_name)
    dests, stars, three_stars = [], [], []
    for ep in range(episodes):
        env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}
        while not done:
            action = policy_fn(env, step_idx)
            _, _, term, trunc, info = env.step(action)
            done = term or trunc
            step_idx += 1
        d = float(info["destruction"])
        s = int(info["stars"])
        dests.append(d)
        stars.append(s)
        three_stars.append(int(s == 3))
    return {
        "agent": strategy_name,
        "base": base_file,
        "army": army_name,
        "episodes": episodes,
        "mean_dest_pct": round(float(np.mean(dests)) * 100.0, 4),
        "std_dest_pct": round(float(np.std(dests)) * 100.0, 4),
        "min_dest_pct": round(float(np.min(dests)) * 100.0, 4),
        "max_dest_pct": round(float(np.max(dests)) * 100.0, 4),
        "unique_dest_outcomes": len(set(round(d, 4) for d in dests)),
        "mean_stars": round(float(np.mean(stars)), 4),
        "three_star_pct": round(float(np.mean(three_stars)) * 100.0, 4),
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_3stars": three_stars,
    }


def _eval_random_masked_pair(args):
    base_file, army_name, episodes = args
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army_name], shaping_mode="stars_aware")
    dests, stars, three_stars = [], [], []
    for ep in range(episodes):
        env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}
        rng = np.random.default_rng(seed=ep)
        while not done:
            mask = env.action_masks()
            valid_actions = np.where(mask)[0]
            act = int(rng.choice(valid_actions))
            _, _, term, trunc, info = env.step(act)
            done = term or trunc
            step_idx += 1
        d = float(info["destruction"])
        s = int(info["stars"])
        dests.append(d)
        stars.append(s)
        three_stars.append(int(s == 3))
    return {
        "agent": "random_masked",
        "base": base_file,
        "army": army_name,
        "episodes": episodes,
        "mean_dest_pct": round(float(np.mean(dests)) * 100.0, 4),
        "std_dest_pct": round(float(np.std(dests)) * 100.0, 4),
        "min_dest_pct": round(float(np.min(dests)) * 100.0, 4),
        "max_dest_pct": round(float(np.max(dests)) * 100.0, 4),
        "unique_dest_outcomes": len(set(round(d, 4) for d in dests)),
        "mean_stars": round(float(np.mean(stars)), 4),
        "three_star_pct": round(float(np.mean(three_stars)) * 100.0, 4),
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_3stars": three_stars,
    }


def _eval_ppo_seed_pair(args):
    model_path_str, base_file, army_name, episodes = args
    from sb3_contrib import MaskablePPO
    model_path = Path(model_path_str)
    model = MaskablePPO.load(model_path)
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army_name], shaping_mode="stars_aware")
    dests, stars, three_stars = [], [], []

    action_counts = {}
    distinct_sectors_list = []
    wb_deployed_count = 0
    wb_steps_list = []
    single_sector_episodes = 0

    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}
        ep_sectors = []
        ep_has_wb = False
        while not done:
            mask = env.action_masks()
            act, _ = model.predict(obs, action_masks=mask, deterministic=True)
            act = int(act)
            action_counts[act] = action_counts.get(act, 0) + 1
            if act > 0:
                idx = act - 1
                k_idx = idx // NUM_SECTORS
                sec = idx % NUM_SECTORS
                ep_sectors.append(sec)
                troop_name = env.troop_keys[k_idx]
                if "wall_breaker" in troop_name:
                    if not ep_has_wb:
                        ep_has_wb = True
                        wb_deployed_count += 1
                        wb_steps_list.append(step_idx)
            obs, _, term, trunc, info = env.step(act)
            done = term or trunc
            step_idx += 1

        d = float(info["destruction"])
        s = int(info["stars"])
        dests.append(d)
        stars.append(s)
        three_stars.append(int(s == 3))

        n_distinct = len(set(ep_sectors))
        distinct_sectors_list.append(n_distinct)
        if ep_sectors:
            counts = [ep_sectors.count(x) for x in set(ep_sectors)]
            if max(counts) / len(ep_sectors) > 0.90:
                single_sector_episodes += 1

    total_actions = sum(action_counts.values()) or 1
    entropy = -sum((c / total_actions) * math.log(c / total_actions) for c in action_counts.values())
    unique_sectors = sorted(list(set(k % NUM_SECTORS for k in action_counts if k > 0)))

    diag = {
        "model_file": model_path.name,
        "model_date": datetime.fromtimestamp(model_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "base": base_file,
        "army": army_name,
        "episodes": episodes,
        "sectors_used": str(unique_sectors),
        "avg_distinct_sectors_per_ep": round(float(np.mean(distinct_sectors_list)), 2),
        "action_entropy": round(entropy, 4),
        "wb_deploy_fraction": round(wb_deployed_count / max(1, episodes), 4) if "wb" in army_name else 0.0,
        "wb_avg_step": round(float(np.mean(wb_steps_list)), 1) if wb_steps_list else -1.0,
        "single_sector_fraction": round(single_sector_episodes / episodes, 4),
        "is_single_sector_over_90pct": (single_sector_episodes / episodes) > 0.90,
    }

    res = {
        "agent": "maskable_ppo",
        "base": base_file,
        "army": army_name,
        "episodes": episodes,
        "mean_dest_pct": round(float(np.mean(dests)) * 100.0, 4),
        "std_dest_pct": round(float(np.std(dests)) * 100.0, 4),
        "min_dest_pct": round(float(np.min(dests)) * 100.0, 4),
        "max_dest_pct": round(float(np.max(dests)) * 100.0, 4),
        "unique_dest_outcomes": len(set(round(d, 4) for d in dests)),
        "mean_stars": round(float(np.mean(stars)), 4),
        "three_star_pct": round(float(np.mean(three_stars)) * 100.0, 4),
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_3stars": three_stars,
        "diag": diag,
    }
    return res


def bootstrap_ci(values: list[float], n_boot: int = 10000, seed: int = 42) -> tuple[float, float, float]:
    arr = np.array(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    n = len(arr)
    indices = rng.integers(0, n, size=(n_boot, n))
    boot_means = np.mean(arr[indices], axis=1)
    lo = float(np.percentile(boot_means, 2.5))
    hi = float(np.percentile(boot_means, 97.5))
    return float(np.mean(arr)), lo, hi


def run_evaluation():
    print("=== Milestone M7b Part B: Held-Out Evaluation ===")
    models_dir = Path("models")
    existing_models = [models_dir / f"ppo_m7b_seed{s}.zip" for s in PPO_SEEDS if (models_dir / f"ppo_m7b_seed{s}.zip").exists()]
    assert existing_models, f"No trained PPO models found in {models_dir}"
    print(f"Bases: {HELD_OUT_BASES} (4 bases)")
    print(f"Armies: {ARMIES} (4 armies)")
    print(f"PPO models: {[m.name for m in existing_models]}")

    workers = min(2, os.cpu_count() or 1)
    t0 = time.perf_counter()

    # 1. Evaluate baselines
    baseline_tasks = [(s, b, a, EPISODES_PER_PAIR) for s in ["left_wave", "surround", "smart_funnel"] for b in HELD_OUT_BASES for a in ARMIES]
    print(f"\n--- Running Baseline Strategies ({len(baseline_tasks)} tasks) ---", flush=True)
    baseline_results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_baseline_pair, baseline_tasks), 1):
            baseline_results.append(res)
            if idx % 8 == 0 or idx == len(baseline_tasks):
                print(f"[{idx}/{len(baseline_tasks)}] {res['agent']} / {res['base']} / {res['army']} ({time.perf_counter() - t0:.1f}s)", flush=True)

    # 2. Evaluate random_masked
    print("\n--- Running Random Masked ---", flush=True)
    random_tasks = [(b, a, EPISODES_PER_PAIR) for b in HELD_OUT_BASES for a in ARMIES]
    random_results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_random_masked_pair, random_tasks), 1):
            random_results.append(res)
            if idx % 8 == 0 or idx == len(random_tasks):
                print(f"[{idx}/{len(random_tasks)}] random_masked / {res['base']} / {res['army']} ({time.perf_counter() - t0:.1f}s)", flush=True)

    # 3. Evaluate PPO (ensemble over seeds)
    print("\n--- Running MaskablePPO Models ---", flush=True)
    ppo_tasks = [(str(m), b, a, EPISODES_PER_PAIR) for m in existing_models for b in HELD_OUT_BASES for a in ARMIES]
    raw_ppo_results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_ppo_seed_pair, ppo_tasks), 1):
            raw_ppo_results.append(res)
            if idx % 8 == 0 or idx == len(ppo_tasks):
                print(f"[{idx}/{len(ppo_tasks)}] ppo / {res['diag']['model_file']} / {res['base']} / {res['army']} ({time.perf_counter() - t0:.1f}s)", flush=True)

    # Aggregate PPO across seeds per (base, army) pair
    ppo_results_by_pair = {}
    all_diags = []
    for r in raw_ppo_results:
        all_diags.append(r["diag"])
        key = (r["base"], r["army"])
        if key not in ppo_results_by_pair:
            ppo_results_by_pair[key] = {"dests": [], "stars": [], "3stars": []}
        ppo_results_by_pair[key]["dests"].extend(r["raw_dests"])
        ppo_results_by_pair[key]["stars"].extend(r["raw_stars"])
        ppo_results_by_pair[key]["3stars"].extend(r["raw_3stars"])

    ppo_pair_results = []
    for (b, a), data in ppo_results_by_pair.items():
        ppo_pair_results.append({
            "agent": "maskable_ppo",
            "base": b,
            "army": a,
            "episodes": len(data["dests"]),
            "mean_dest_pct": round(float(np.mean(data["dests"])) * 100.0, 4),
            "std_dest_pct": round(float(np.std(data["dests"])) * 100.0, 4),
            "min_dest_pct": round(float(np.min(data["dests"])) * 100.0, 4),
            "max_dest_pct": round(float(np.max(data["dests"])) * 100.0, 4),
            "unique_dest_outcomes": len(set(round(d, 4) for d in data["dests"])),
            "mean_stars": round(float(np.mean(data["stars"])), 4),
            "three_star_pct": round(float(np.mean(data["3stars"])) * 100.0, 4),
            "raw_dests": data["dests"],
            "raw_stars": data["stars"],
            "raw_3stars": data["3stars"],
        })

    # Save diagnostics CSV
    diag_csv = ROOT / "results" / "ppo_action_diagnostics_partB.csv"
    diag_csv.parent.mkdir(parents=True, exist_ok=True)
    with diag_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_diags[0].keys()))
        writer.writeheader()
        writer.writerows(all_diags)
    print(f"\nWrote PPO action diagnostics to {diag_csv}")

    # Combine all results into summary CSV
    all_summary_rows = []
    for r in baseline_results + random_results + ppo_pair_results:
        row = dict(r)
        row.pop("raw_dests", None)
        row.pop("raw_stars", None)
        row.pop("raw_3stars", None)
        row.pop("diag", None)
        all_summary_rows.append(row)

    out_csv = ROOT / "results" / "m7b_partB.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_summary_rows)
    print(f"Wrote per-pair evaluation to {out_csv}")

    # Bootstrap 95% CIs over the 16 independent (base, army) pairs
    print("\n" + "=" * 90)
    print("M7b Part B SUMMARY ACROSS 16 INDEPENDENT PAIRS (BOOTSTRAP 95% CONFIDENCE INTERVALS)")
    print("=" * 90)
    print(f"{'Agent':<16} {'Mean Dest % [95% CI]':<26} {'Mean Stars [95% CI]':<24} {'3-Star Rate % [95% CI]':<24}")
    print("-" * 90)

    agent_metrics = {}
    for agent_name in ["left_wave", "surround", "smart_funnel", "random_masked", "maskable_ppo"]:
        rows = [r for r in all_summary_rows if r["agent"] == agent_name]
        d_vals = [r["mean_dest_pct"] for r in rows]
        s_vals = [r["mean_stars"] for r in rows]
        r3_vals = [r["three_star_pct"] for r in rows]

        d_m, d_lo, d_hi = bootstrap_ci(d_vals)
        s_m, s_lo, s_hi = bootstrap_ci(s_vals)
        r3_m, r3_lo, r3_hi = bootstrap_ci(r3_vals)

        agent_metrics[agent_name] = {"dest": (d_m, d_lo, d_hi), "stars": (s_m, s_lo, s_hi), "r3": (r3_m, r3_lo, r3_hi)}
        print(f"{agent_name:<16} {d_m:5.2f}% [{d_lo:5.2f}, {d_hi:5.2f}]   {s_m:4.2f} [{s_lo:4.2f}, {s_hi:4.2f}]     {r3_m:5.2f}% [{r3_lo:5.2f}, {r3_hi:5.2f}]")

    # Paired delta
    ppo_rows = { (r["base"], r["army"]): r for r in all_summary_rows if r["agent"] == "maskable_ppo" }
    lw_rows = { (r["base"], r["army"]): r for r in all_summary_rows if r["agent"] == "left_wave" }
    delta_dest = [ppo_rows[k]["mean_dest_pct"] - lw_rows[k]["mean_dest_pct"] for k in ppo_rows]
    delta_stars = [ppo_rows[k]["mean_stars"] - lw_rows[k]["mean_stars"] for k in ppo_rows]

    dd_m, dd_lo, dd_hi = bootstrap_ci(delta_dest)
    ds_m, ds_lo, ds_hi = bootstrap_ci(delta_stars)

    print("\n" + "=" * 90)
    print("PAIRED HEAD-TO-HEAD: MASKABLE_PPO vs LEFT_WAVE (BEST BASELINE)")
    print("=" * 90)
    print(f"Paired delta destruction: {dd_m:+.2f} pp [95% CI {dd_lo:+.2f}, {dd_hi:+.2f}]")
    print(f"Paired delta stars:       {ds_m:+.3f} [95% CI {ds_lo:+.3f}, {ds_hi:+.3f}]")
    print(f"Does PPO beat best baseline on destruction? {'YES' if dd_m > 0 else 'NO'}")
    print(f"Does PPO beat best baseline on stars?       {'YES' if ds_m > 0 else 'NO'}")


if __name__ == "__main__":
    run_evaluation()

