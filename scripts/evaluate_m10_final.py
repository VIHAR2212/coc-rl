"""M10 Step 1g: Final Benchmark on Fresh Held-Out Set (heldout_v2) & Secondary Check on Old Bases.

Key Features:
1. Single-use guard: refuses to run on data/bases_gen/heldout_v2 if results/heldout_v2_usage.log
   exists, unless --allow-rerun is passed.
2. Evaluates:
   - left_wave
   - random_masked
   - ppo_m9_bcft (seeds 42, 43, 44 & 3-seed aggregate)
   - ppo_m10_bc (seeds 42, 43, 44 & 3-seed aggregate)
   - ppo_m10_bcft (seeds 42, 43, 44 & 3-seed aggregate)
   on 30 fresh held-out layouts x 7 TH8 armies x 20 episodes (seeds 0..19).
3. Reports:
   - Mean destruction %, mean stars, 3-star %, Town Hall kill %, 50%-crossing %
   - For all armies, 4 ground armies, and all non-dragon armies
4. Paired bootstrap resampling LAYOUTS (not individual pairs) with 95% CIs vs left_wave and ppo_m9_bcft.
5. Secondary check: evaluates the three M10 BC+PPO seeds on old bases (base07..10 x 7 armies x 100 episodes).
"""

import argparse
import csv
from datetime import datetime
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import numpy as np
from sb3_contrib import MaskablePPO

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents import STRATEGIES
from sim.env import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv

DATA_DIR = ROOT / "data"
HELDOUT_V2_DIR = DATA_DIR / "bases_gen" / "heldout_v2"
OLD_HELDOUT_DIR = DATA_DIR / "bases"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
USAGE_LOG = RESULTS_DIR / "heldout_v2_usage.log"
MODELS_DIR = ROOT / "models"

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


def check_single_use_guard(allow_rerun: bool):
    if USAGE_LOG.exists() and not allow_rerun:
        content = USAGE_LOG.read_text(encoding="utf-8").strip()
        if content:
            print(f"\n{'!'*80}")
            print("ERROR: heldout_v2 is SINGLE-USE and has already been evaluated!")
            print(f"Log contents in {USAGE_LOG}:\n{content}")
            print("Pass --allow-rerun if you explicitly intend to evaluate again.")
            print(f"{'!'*80}\n")
            sys.exit(1)

    # Log usage
    try:
        git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    except Exception:
        git_hash = "unknown"

    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] Evaluated on heldout_v2 | git: {git_hash} | argv: {' '.join(sys.argv)}\n"
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)
    print(f"Logged heldout_v2 access in {USAGE_LOG.name}.")


def _eval_baseline_layout_army(args):
    strat_name, layout_path_str, army_name, episodes = args
    policy_fn = STRATEGIES[strat_name]
    env = CoCEnv(base_file=layout_path_str, army=army_name)

    dests, stars, three_stars, th_kills, cross_50s = [], [], [], [], []
    for ep in range(episodes):
        obs, info = env.reset(seed=ep)
        done = False
        step_idx = 0
        while not done:
            action = policy_fn(env, step_idx)
            obs, reward, term, trunc, info = env.step(action)
            done = term or trunc
            step_idx += 1

        d = float(info.get("destruction", 0.0)) * 100.0
        s = int(info.get("stars", 0))
        th = 1 if getattr(env, "th_destroyed", False) else 0

        dests.append(d)
        stars.append(s)
        three_stars.append(1 if s == 3 else 0)
        th_kills.append(th)
        cross_50s.append(1 if d >= 50.0 else 0)

    return {
        "agent": strat_name,
        "base": Path(layout_path_str).name,
        "army": army_name,
        "episodes": episodes,
        "mean_dest": float(np.mean(dests)),
        "mean_stars": float(np.mean(stars)),
        "three_star_rate": float(np.mean(three_stars)) * 100.0,
        "th_kill_rate": float(np.mean(th_kills)) * 100.0,
        "cross_50_rate": float(np.mean(cross_50s)) * 100.0,
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_th": th_kills,
    }


def _eval_random_masked_layout_army(args):
    layout_path_str, army_name, episodes = args
    env = ActionMaskCoCEnv(bases=[layout_path_str], armies=[army_name], shaping_mode="stars_aware")

    dests, stars, three_stars, th_kills, cross_50s = [], [], [], [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        rng = np.random.default_rng(ep)
        done = False
        info = {}
        while not done:
            mask = env.action_masks()
            valid = np.where(mask)[0]
            act = int(rng.choice(valid))
            obs, _, term, trunc, info = env.step(act)
            done = term or trunc

        d = float(info.get("destruction", 0.0)) * 100.0
        s = int(info.get("stars", 0))
        th = 1 if getattr(env.env, "th_destroyed", False) else 0

        dests.append(d)
        stars.append(s)
        three_stars.append(1 if s == 3 else 0)
        th_kills.append(th)
        cross_50s.append(1 if d >= 50.0 else 0)

    return {
        "agent": "random_masked",
        "base": Path(layout_path_str).name,
        "army": army_name,
        "episodes": episodes,
        "mean_dest": float(np.mean(dests)),
        "mean_stars": float(np.mean(stars)),
        "three_star_rate": float(np.mean(three_stars)) * 100.0,
        "th_kill_rate": float(np.mean(th_kills)) * 100.0,
        "cross_50_rate": float(np.mean(cross_50s)) * 100.0,
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_th": th_kills,
    }


_MODEL_CACHE: dict[str, Any] = {}


def _get_model(model_path_str: str) -> Any:
    if model_path_str not in _MODEL_CACHE:
        _MODEL_CACHE[model_path_str] = MaskablePPO.load(model_path_str, device="cpu")
    return _MODEL_CACHE[model_path_str]


def _eval_model_layout_army(args):
    agent_name, model_path_str, layout_path_str, army_name, episodes = args
    model = _get_model(model_path_str)
    env = ActionMaskCoCEnv(bases=[layout_path_str], armies=[army_name], shaping_mode="stars_aware")

    dests, stars, three_stars, th_kills, cross_50s = [], [], [], [], []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done = False
        info = {}
        while not done:
            mask = env.action_masks()
            act, _ = model.predict(obs, action_masks=mask, deterministic=True)
            obs, _, term, trunc, info = env.step(int(act))
            done = term or trunc

        d = float(info.get("destruction", 0.0)) * 100.0
        s = int(info.get("stars", 0))
        th = 1 if getattr(env.env, "th_destroyed", False) else 0

        dests.append(d)
        stars.append(s)
        three_stars.append(1 if s == 3 else 0)
        th_kills.append(th)
        cross_50s.append(1 if d >= 50.0 else 0)

    return {
        "agent": agent_name,
        "base": Path(layout_path_str).name,
        "army": army_name,
        "episodes": episodes,
        "mean_dest": float(np.mean(dests)),
        "mean_stars": float(np.mean(stars)),
        "three_star_rate": float(np.mean(three_stars)) * 100.0,
        "th_kill_rate": float(np.mean(th_kills)) * 100.0,
        "cross_50_rate": float(np.mean(cross_50s)) * 100.0,
        "raw_dests": dests,
        "raw_stars": stars,
        "raw_th": th_kills,
    }


def bootstrap_resample_layouts(
    agent_results: dict[str, dict[tuple[str, str], dict[str, Any]]],
    agent_name: str,
    ref_agent_name: str,
    layouts: list[str],
    armies: list[str],
    n_boot: int = 2000,
    seed: int = 42,
) -> dict[str, Any]:
    """Paired bootstrap resampling LAYOUTS with replacement."""
    rng = np.random.default_rng(seed)
    n_layouts = len(layouts)

    dests = []
    stars = []
    th_kills = []
    delta_dests = []
    delta_stars = []

    for _ in range(n_boot):
        sample_layouts = rng.choice(layouts, size=n_layouts, replace=True)

        d_agent, s_agent, th_agent = [], [], []
        d_ref, s_ref, th_ref = [], [], []

        for l in sample_layouts:
            for a in armies:
                row_agent = agent_results[agent_name][(l, a)]
                d_agent.append(row_agent["mean_dest"])
                s_agent.append(row_agent["mean_stars"])
                th_agent.append(row_agent["th_kill_rate"])

                if ref_agent_name and ref_agent_name in agent_results:
                    row_ref = agent_results[ref_agent_name][(l, a)]
                    d_ref.append(row_ref["mean_dest"])
                    s_ref.append(row_ref["mean_stars"])
                    th_ref.append(row_ref["th_kill_rate"])

        m_d = float(np.mean(d_agent))
        m_s = float(np.mean(s_agent))
        m_th = float(np.mean(th_agent))

        dests.append(m_d)
        stars.append(m_s)
        th_kills.append(m_th)

        if ref_agent_name and d_ref:
            delta_dests.append(m_d - float(np.mean(d_ref)))
            delta_stars.append(m_s - float(np.mean(s_ref)))

    return {
        "dest_mean": float(np.mean(dests)),
        "dest_ci": (float(np.percentile(dests, 2.5)), float(np.percentile(dests, 97.5))),
        "stars_mean": float(np.mean(stars)),
        "stars_ci": (float(np.percentile(stars, 2.5)), float(np.percentile(stars, 97.5))),
        "th_mean": float(np.mean(th_kills)),
        "th_ci": (float(np.percentile(th_kills, 2.5)), float(np.percentile(th_kills, 97.5))),
        "delta_dest": (float(np.mean(delta_dests)), float(np.percentile(delta_dests, 2.5)), float(np.percentile(delta_dests, 97.5))) if delta_dests else (0.0, 0.0, 0.0),
        "delta_stars": (float(np.mean(delta_stars)), float(np.percentile(delta_stars, 2.5)), float(np.percentile(delta_stars, 97.5))) if delta_stars else (0.0, 0.0, 0.0),
    }


def main():
    parser = argparse.ArgumentParser(description="M10 Final Evaluation on fresh heldout_v2 and secondary old bases")
    parser.add_argument("--allow-rerun", action="store_true", help="Allow re-running evaluation on single-use heldout_v2")
    parser.add_argument("--secondary-only", action="store_true", help="Only run secondary evaluation on old bases")
    args = parser.parse_args()

    if not args.secondary_only:
        check_single_use_guard(args.allow_rerun)

    # 1. Fresh Held-out v2 Evaluation
    heldout_layouts = sorted(HELDOUT_V2_DIR.glob("heldout_base_*.json"))
    layout_names = [p.name for p in heldout_layouts]
    print(f"\nFresh Held-Out Layouts: {len(heldout_layouts)} layouts in {HELDOUT_V2_DIR.name}")

    models_to_eval = [
        ("ppo_m9_bcft_seed42", MODELS_DIR / "ppo_m9_bcft_seed42.zip"),
        ("ppo_m9_bcft_seed43", MODELS_DIR / "ppo_m9_bcft_seed43.zip"),
        ("ppo_m9_bcft_seed44", MODELS_DIR / "ppo_m9_bcft_seed44.zip"),
        ("ppo_m10_bc_seed42", MODELS_DIR / "ppo_m10_bc_seed42.zip"),
        ("ppo_m10_bc_seed43", MODELS_DIR / "ppo_m10_bc_seed43.zip"),
        ("ppo_m10_bc_seed44", MODELS_DIR / "ppo_m10_bc_seed44.zip"),
        ("ppo_m10_bcft_seed42", MODELS_DIR / "ppo_m10_bcft_seed42.zip"),
        ("ppo_m10_bcft_seed43", MODELS_DIR / "ppo_m10_bcft_seed43.zip"),
        ("ppo_m10_bcft_seed44", MODELS_DIR / "ppo_m10_bcft_seed44.zip"),
    ]

    all_agent_pair_results: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    csv_rows: list[dict[str, Any]] = []

    with multiprocessing.Pool(processes=2) as pool:
        # Baselines
        for strat in ["left_wave", "random_masked"]:
            print(f"\nEvaluating baseline {strat} on heldout_v2...", flush=True)
            all_agent_pair_results[strat] = {}
            if strat == "left_wave":
                tasks = [("left_wave", str(l_p), army, 20) for l_p in heldout_layouts for army in ARMIES]
                results = pool.map(_eval_baseline_layout_army, tasks)
            else:
                tasks = [(str(l_p), army, 20) for l_p in heldout_layouts for army in ARMIES]
                results = pool.map(_eval_random_masked_layout_army, tasks)
            for res in results:
                all_agent_pair_results[strat][(res["base"], res["army"])] = res
                csv_rows.append(res)

        # Models
        for ag_name, m_path in models_to_eval:
            if not m_path.exists():
                print(f"WARNING: Model {m_path.name} not found, skipping.")
                continue
            print(f"Evaluating {ag_name} on heldout_v2...", flush=True)
            all_agent_pair_results[ag_name] = {}
            tasks = [(ag_name, str(m_path), str(l_p), army, 20) for l_p in heldout_layouts for army in ARMIES]
            results = pool.map(_eval_model_layout_army, tasks)
            for res in results:
                all_agent_pair_results[ag_name][(res["base"], res["army"])] = res
                csv_rows.append(res)

    # Compute 3-seed aggregates for m9_bcft, m10_bc, m10_bcft
    for prefix in ["ppo_m9_bcft", "ppo_m10_bc", "ppo_m10_bcft"]:
        agg_name = f"{prefix}_3seed"
        seeds = [f"{prefix}_seed42", f"{prefix}_seed43", f"{prefix}_seed44"]
        if all(s in all_agent_pair_results for s in seeds):
            all_agent_pair_results[agg_name] = {}
            for l_name in layout_names:
                for army in ARMIES:
                    seed_rows = [all_agent_pair_results[s][(l_name, army)] for s in seeds]
                    agg_res = {
                        "agent": agg_name,
                        "base": l_name,
                        "army": army,
                        "episodes": 60,
                        "mean_dest": float(np.mean([r["mean_dest"] for r in seed_rows])),
                        "mean_stars": float(np.mean([r["mean_stars"] for r in seed_rows])),
                        "three_star_rate": float(np.mean([r["three_star_rate"] for r in seed_rows])),
                        "th_kill_rate": float(np.mean([r["th_kill_rate"] for r in seed_rows])),
                        "cross_50_rate": float(np.mean([r["cross_50_rate"] for r in seed_rows])),
                    }
                    all_agent_pair_results[agg_name][(l_name, army)] = agg_res
                    csv_rows.append(agg_res)

    # Save per-pair CSV
    raw_csv_path = RESULTS_DIR / "m10_heldout_v2_all_pairs.csv"
    fieldnames = ["agent", "base", "army", "episodes", "mean_dest", "mean_stars", "three_star_rate", "th_kill_rate", "cross_50_rate"]
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\nSaved raw records to {raw_csv_path.name}.")

    # Summary table generation with Layout-resampling bootstrap
    summary_rows = []
    subsets = [
        ("All 7 Armies (30 Layouts)", ARMIES),
        ("4 Ground Armies (30 Layouts)", GROUND_ARMIES),
        ("24 Non-Dragon Armies (30 Layouts)", NON_DRAGON_ARMIES),
    ]

    print("\n" + "=" * 90)
    print("M10 HELDOUT_V2 SUMMARY (Layout-Resampling Bootstrap 95% CIs)")
    print("=" * 90)

    for subset_name, army_list in subsets:
        print(f"\n--- {subset_name} ---")
        print(f"{'Agent':<24} {'Dest % [95% CI]':<24} {'Stars [95% CI]':<20} {'3-Star %':<10} {'TH-Kill %':<10} {'dDest vs LW':<20} {'dStars vs LW':<16}")
        print("-" * 120)

        for agent in all_agent_pair_results:
            b_stats_lw = bootstrap_resample_layouts(
                all_agent_pair_results, agent, "left_wave", layout_names, army_list, n_boot=1500
            )
            b_stats_m9 = bootstrap_resample_layouts(
                all_agent_pair_results, agent, "ppo_m9_bcft_3seed", layout_names, army_list, n_boot=1500
            )

            # Direct means
            agent_rows = [all_agent_pair_results[agent][(l, a)] for l in layout_names for a in army_list]
            m_dest = float(np.mean([r["mean_dest"] for r in agent_rows]))
            m_stars = float(np.mean([r["mean_stars"] for r in agent_rows]))
            m_3star = float(np.mean([r["three_star_rate"] for r in agent_rows]))
            m_th = float(np.mean([r["th_kill_rate"] for r in agent_rows]))
            m_50 = float(np.mean([r["cross_50_rate"] for r in agent_rows]))

            dest_str = f"{m_dest:5.2f} [{b_stats_lw['dest_ci'][0]:5.2f}, {b_stats_lw['dest_ci'][1]:5.2f}]"
            stars_str = f"{m_stars:4.2f} [{b_stats_lw['stars_ci'][0]:4.2f}, {b_stats_lw['stars_ci'][1]:4.2f}]"
            dlw_dest_str = f"{b_stats_lw['delta_dest'][0]:+5.2f} [{b_stats_lw['delta_dest'][1]:+5.2f}, {b_stats_lw['delta_dest'][2]:+5.2f}]" if agent != "left_wave" else "-"
            dlw_stars_str = f"{b_stats_lw['delta_stars'][0]:+5.2f} [{b_stats_lw['delta_stars'][1]:+5.2f}, {b_stats_lw['delta_stars'][2]:+5.2f}]" if agent != "left_wave" else "-"

            print(f"{agent:<24} {dest_str:<24} {stars_str:<20} {m_3star:5.2f}%    {m_th:5.2f}%    {dlw_dest_str:<20} {dlw_stars_str:<16}")

            summary_rows.append({
                "subset": subset_name,
                "agent": agent,
                "mean_dest": round(m_dest, 2),
                "dest_ci_lo": round(b_stats_lw["dest_ci"][0], 2),
                "dest_ci_hi": round(b_stats_lw["dest_ci"][1], 2),
                "mean_stars": round(m_stars, 2),
                "stars_ci_lo": round(b_stats_lw["stars_ci"][0], 2),
                "stars_ci_hi": round(b_stats_lw["stars_ci"][1], 2),
                "three_star_rate": round(m_3star, 2),
                "th_kill_rate": round(m_th, 2),
                "cross_50_rate": round(m_50, 2),
                "delta_dest_vs_lw": round(b_stats_lw["delta_dest"][0], 2),
                "delta_dest_ci_lo": round(b_stats_lw["delta_dest"][1], 2),
                "delta_dest_ci_hi": round(b_stats_lw["delta_dest"][2], 2),
                "delta_stars_vs_lw": round(b_stats_lw["delta_stars"][0], 2),
                "delta_stars_ci_lo": round(b_stats_lw["delta_stars"][1], 2),
                "delta_stars_ci_hi": round(b_stats_lw["delta_stars"][2], 2),
                "delta_dest_vs_m9": round(b_stats_m9["delta_dest"][0], 2),
                "delta_dest_ci_lo_m9": round(b_stats_m9["delta_dest"][1], 2),
                "delta_dest_ci_hi_m9": round(b_stats_m9["delta_dest"][2], 2),
                "delta_stars_vs_m9": round(b_stats_m9["delta_stars"][0], 2),
                "delta_stars_ci_lo_m9": round(b_stats_m9["delta_stars"][1], 2),
                "delta_stars_ci_hi_m9": round(b_stats_m9["delta_stars"][2], 2),
            })

    summary_csv_path = RESULTS_DIR / "m10_heldout_v2_summary.csv"
    with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\nSaved summary to {summary_csv_path.name}.")

    # 2. Secondary Check: Evaluate M10 BC+PPO seeds on Old Bases (base07..base10)
    print("\n" + "=" * 90)
    print("M10 SECONDARY CHECK: Old Bases (base07..10 x 7 armies x 100 episodes, seeds 0..99)")
    print("[Previously Used Layouts Suite]")
    print("=" * 90)

    old_bases = [f"base{i:02d}.json" for i in range(7, 11)]
    old_csv_rows = []

    m10_ft_seeds = [
        ("ppo_m10_bcft_seed42", MODELS_DIR / "ppo_m10_bcft_seed42.zip"),
        ("ppo_m10_bcft_seed43", MODELS_DIR / "ppo_m10_bcft_seed43.zip"),
        ("ppo_m10_bcft_seed44", MODELS_DIR / "ppo_m10_bcft_seed44.zip"),
    ]

    with multiprocessing.Pool(processes=2) as pool:
        for ag_name, m_path in m10_ft_seeds:
            if not m_path.exists():
                continue
            print(f"Evaluating {ag_name} on 28 old pairs (100 episodes per pair)...", flush=True)
            tasks = [(ag_name, str(m_path), str(OLD_HELDOUT_DIR / b), army, 100) for b in old_bases for army in ARMIES]
            results = pool.map(_eval_model_layout_army, tasks)
            for res in results:
                old_csv_rows.append(res)

    if old_csv_rows:
        old_csv_path = RESULTS_DIR / "m10_secondary_old_heldout.csv"
        with open(old_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(old_csv_rows)
        print(f"Saved secondary check to {old_csv_path.name}.")


if __name__ == "__main__":
    main()
