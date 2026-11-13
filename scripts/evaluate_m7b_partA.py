"""Milestone M7b Part A: Evaluation of baselines, random_masked, and MaskablePPO on held-out bases (base07 to base10)."""
import argparse
import csv
import json
import math
import os
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["PYTHONPATH"] = str(ROOT)

import numpy as np
from sb3_contrib import MaskablePPO

from agents import STRATEGIES
from sim import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

HELD_OUT_BASES_PART_A = [
    "base07.json",
    "base08.json",
    "base09.json",
    "base10.json",
]


def _army_names() -> list[str]:
    raw = json.loads((DATA_DIR / "armies.json").read_text(encoding="utf-8"))
    return [k for k in raw if not k.startswith("_")]


def _run_baseline_combo(args: tuple[str, str, str, int]) -> list[dict]:
    strategy_name, base_file, army_name, episodes = args
    policy_fn = STRATEGIES[strategy_name]
    env = CoCEnv(base_file=base_file, army=army_name)
    rows: list[dict] = []
    for ep in range(episodes):
        env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}
        while not done:
            _, _, term, trunc, info = env.step(policy_fn(env, step_idx))
            done = term or trunc
            step_idx += 1
        dest = float(info["destruction"])
        stars = int(info["stars"])
        rows.append({
            "agent": strategy_name,
            "base": base_file,
            "army": army_name,
            "episode": ep,
            "seed": ep,
            "destruction": round(dest, 6),
            "stars": stars,
            "three_star": int(stars == 3),
            "steps": step_idx,
        })
    return rows


def _run_rl_combo(args: tuple[str, list[str], str, str, int]) -> tuple[list[dict], dict | None]:
    agent_name, model_paths, base_file, army_name, episodes = args
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army_name])
    models = [MaskablePPO.load(p, device="cpu") for p in model_paths] if agent_name == "maskable_ppo" else []
    rows: list[dict] = []

    # Diagnostic accumulators for maskable_ppo
    ep_distinct_sectors = []
    ep_single_sector_flags = []
    all_deployed_sectors = []
    all_actions = []
    wb_deployed_eps = 0
    all_wb_steps = []

    for ep in range(episodes):
        obs, _ = env.reset(seed=ep, options={"base_file": base_file, "army": army_name})
        rng = np.random.default_rng(ep)
        model = models[ep % len(models)] if models else None
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}

        cur_ep_sectors = []
        cur_ep_wb_steps = []

        while not done:
            mask = env.action_masks()
            if agent_name == "maskable_ppo":
                action, _ = model.predict(obs, deterministic=True, action_masks=mask)
                act = int(action)
            else:
                valid = np.flatnonzero(mask)
                act = int(rng.choice(valid))

            all_actions.append(act)

            if act > 0:
                troop_idx = (act - 1) // env.num_sectors
                sector_idx = (act - 1) % env.num_sectors
                cur_ep_sectors.append(sector_idx)
                all_deployed_sectors.append(sector_idx)

                troop_key = env.troop_keys[troop_idx]
                if "wall_breaker" in troop_key:
                    cur_ep_wb_steps.append(step_idx)
                    all_wb_steps.append(step_idx)

            obs, _, term, trunc, info = env.step(act)
            done = term or trunc
            step_idx += 1

        dest = float(info["destruction"])
        stars = int(info["stars"])
        rows.append({
            "agent": agent_name,
            "base": base_file,
            "army": army_name,
            "episode": ep,
            "seed": ep,
            "destruction": round(dest, 6),
            "stars": stars,
            "three_star": int(stars == 3),
            "steps": step_idx,
        })

        if agent_name == "maskable_ppo":
            distinct_s = len(set(cur_ep_sectors)) if cur_ep_sectors else 0
            ep_distinct_sectors.append(distinct_s)
            ep_single_sector_flags.append(distinct_s <= 1)
            if cur_ep_wb_steps:
                wb_deployed_eps += 1

    diag = None
    if agent_name == "maskable_ppo":
        # Compute action entropy
        act_counts = Counter(all_actions)
        tot_acts = len(all_actions)
        entropy = 0.0
        for cnt in act_counts.values():
            p = cnt / tot_acts
            if p > 0:
                entropy -= p * math.log2(p)

        single_frac = float(np.mean(ep_single_sector_flags)) if ep_single_sector_flags else 0.0
        diag = {
            "model_file": Path(model_paths[0]).name if model_paths else "unknown",
            "model_date": "2026-11-12 21:35:44",
            "base": base_file,
            "army": army_name,
            "episodes": episodes,
            "sectors_used": sorted(list(set(all_deployed_sectors))),
            "avg_distinct_sectors_per_ep": round(float(np.mean(ep_distinct_sectors)), 2) if ep_distinct_sectors else 0.0,
            "action_entropy": round(float(entropy), 4),
            "wb_deploy_fraction": round(wb_deployed_eps / episodes, 3),
            "wb_avg_step": round(float(np.mean(all_wb_steps)), 1) if all_wb_steps else -1.0,
            "single_sector_fraction": round(single_frac, 3),
            "is_single_sector_over_90pct": single_frac > 0.90,
        }

    return rows, diag


def _bootstrap_ci(pair_vals: np.ndarray, n_boot: int = 10_000, seed: int = 42) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) across independent (base, army) pairs."""
    rng = np.random.default_rng(seed)
    n = len(pair_vals)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = pair_vals[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(pair_vals.mean()), float(lo), float(hi)


def run_evaluation(episodes=100, workers=None):
    bases = HELD_OUT_BASES_PART_A
    armies = _army_names()
    pairs = [(b, a) for b in bases for a in armies]
    print(f"=== Milestone M7b Part A: Held-Out Evaluation ===")
    print(f"Bases: {bases} ({len(bases)} bases)")
    print(f"Armies: {armies} ({len(armies)} armies)")
    print(f"Total pairs: {len(pairs)} (base, army) pairs")
    print(f"Episodes per pair: {episodes} seeded episodes")

    # Locate current MaskablePPO models
    model_paths = sorted(Path("models").glob("ppo_m7b_seed*.zip"))
    if not model_paths:
        model_paths = [Path("models/ppo_m7b_seed42.zip")]
    print(f"MaskablePPO models: {[p.name for p in model_paths]}")

    max_workers = workers if workers is not None else min(len(pairs), max(1, os.cpu_count() or 1))
    print(f"Workers: {max_workers}")

    baseline_strategies = ["left_wave", "surround", "smart_funnel"]
    all_rows: list[dict] = []
    t0 = time.perf_counter()

    # 1. Run baselines
    print("\n--- Running Baseline Strategies ---")
    base_tasks = [(s, b, a, episodes) for s in baseline_strategies for b, a in pairs]
    if max_workers <= 1:
        for idx, t in enumerate(base_tasks, 1):
            all_rows.extend(_run_baseline_combo(t))
            if idx % 8 == 0 or idx == len(base_tasks):
                print(f"[{idx}/{len(base_tasks)}] {t[0]} / {t[1]} / {t[2]} ({time.perf_counter() - t0:.1f}s)", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for idx, rows in enumerate(pool.map(_run_baseline_combo, base_tasks), 1):
                all_rows.extend(rows)
                if idx % 8 == 0 or idx == len(base_tasks):
                    t = base_tasks[idx - 1]
                    print(f"[{idx}/{len(base_tasks)}] {t[0]} / {t[1]} / {t[2]} ({time.perf_counter() - t0:.1f}s)", flush=True)

    # 2. Run RL agents (random_masked and maskable_ppo)
    print("\n--- Running RL Agents (random_masked and maskable_ppo) ---")
    str_paths = [str(p) for p in model_paths]
    rl_tasks = [
        (agent, str_paths if agent == "maskable_ppo" else [], b, a, episodes)
        for agent in ("random_masked", "maskable_ppo")
        for b, a in pairs
    ]
    diagnostics: list[dict] = []
    if max_workers <= 1:
        for idx, t in enumerate(rl_tasks, 1):
            r_rows, diag = _run_rl_combo(t)
            all_rows.extend(r_rows)
            if diag:
                diagnostics.append(diag)
            if idx % 8 == 0 or idx == len(rl_tasks):
                print(f"[{idx}/{len(rl_tasks)}] {t[0]} / {t[2]} / {t[3]} ({time.perf_counter() - t0:.1f}s)", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for idx, (r_rows, diag) in enumerate(pool.map(_run_rl_combo, rl_tasks), 1):
                all_rows.extend(r_rows)
                if diag:
                    diagnostics.append(diag)
                if idx % 8 == 0 or idx == len(rl_tasks):
                    t = rl_tasks[idx - 1]
                    print(f"[{idx}/{len(rl_tasks)}] {t[0]} / {t[2]} / {t[3]} ({time.perf_counter() - t0:.1f}s)", flush=True)

    elapsed = time.perf_counter() - t0
    print(f"\nAll {len(all_rows)} episodes completed in {elapsed:.1f}s")

    # Save PPO action diagnostics
    diag_csv = RESULTS_DIR / "ppo_action_diagnostics.csv"
    if diagnostics:
        diag_fields = [
            "model_file", "model_date", "base", "army", "episodes", "sectors_used",
            "avg_distinct_sectors_per_ep", "action_entropy", "wb_deploy_fraction",
            "wb_avg_step", "single_sector_fraction", "is_single_sector_over_90pct",
        ]
        with diag_csv.open("w", newline="", encoding="utf-8") as f:
            dw = csv.DictWriter(f, fieldnames=diag_fields)
            dw.writeheader()
            dw.writerows(diagnostics)
        print(f"Wrote PPO action diagnostics to {diag_csv}")

    # 3. Analyze seed variance per pair
    print("\n" + "=" * 80)
    print("STEP 1: SEED VARIANCE CHECK PER (BASE, ARMY) PAIR (100 EPISODES EACH)")
    print("=" * 80)
    agents_order = ["left_wave", "surround", "smart_funnel", "random_masked", "maskable_ppo"]

    pair_rows: list[dict] = []
    pair_stats: dict[str, dict[str, np.ndarray]] = {
        ag: {"dest": np.zeros(len(pairs)), "stars": np.zeros(len(pairs)), "three": np.zeros(len(pairs))}
        for ag in agents_order
    }

    variance_summary = {}
    for ag in agents_order:
        nonzero_var_pairs = 0
        total_pairs = len(pairs)
        print(f"\nAgent: {ag}")
        print(f"{'Base':<12} {'Army':<14} {'Mean Dest %':>12} {'Std Dev':>9} {'Min %':>7} {'Max %':>7} {'Unique Dests':>13}")
        print("-" * 76)
        for p_idx, (b, a) in enumerate(pairs):
            sub = [r for r in all_rows if r["agent"] == ag and r["base"] == b and r["army"] == a]
            dests = np.array([r["destruction"] for r in sub], dtype=np.float64) * 100.0
            stars = np.array([r["stars"] for r in sub], dtype=np.float64)
            threes = np.array([r["three_star"] for r in sub], dtype=np.float64) * 100.0

            md = float(dests.mean())
            sd = float(dests.std())
            min_d = float(dests.min())
            max_d = float(dests.max())
            uniq = len(set(np.round(dests, 4)))

            ms = float(stars.mean())
            m3 = float(threes.mean())

            if sd > 1e-4:
                nonzero_var_pairs += 1

            pair_stats[ag]["dest"][p_idx] = md
            pair_stats[ag]["stars"][p_idx] = ms
            pair_stats[ag]["three"][p_idx] = m3

            pair_rows.append({
                "agent": ag,
                "base": b,
                "army": a,
                "episodes": len(sub),
                "mean_dest_pct": round(md, 4),
                "std_dest_pct": round(sd, 4),
                "min_dest_pct": round(min_d, 4),
                "max_dest_pct": round(max_d, 4),
                "unique_dest_outcomes": uniq,
                "mean_stars": round(ms, 4),
                "three_star_pct": round(m3, 4),
            })
            print(f"{b:<12} {a:<14} {md:11.2f}% {sd:9.2f} {min_d:6.1f}% {max_d:6.1f}% {uniq:12d}")
        variance_summary[ag] = (nonzero_var_pairs, total_pairs)
        print(f"-> Pairs with non-zero seed variance: {nonzero_var_pairs} / {total_pairs} ({nonzero_var_pairs/total_pairs*100:.1f}%)")

    # 4. Save results to results/m7b_partA.csv
    out_csv = RESULTS_DIR / "m7b_partA.csv"
    fields = [
        "agent", "base", "army", "episodes", "mean_dest_pct", "std_dest_pct",
        "min_dest_pct", "max_dest_pct", "unique_dest_outcomes", "mean_stars", "three_star_pct",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(pair_rows)
    print(f"\nWrote per-pair evaluation to {out_csv}")

    # Also save raw episodes
    raw_episodes_csv = RESULTS_DIR / "m7b_partA_episodes.csv"
    with raw_episodes_csv.open("w", newline="", encoding="utf-8") as f:
        ew = csv.DictWriter(f, fieldnames=["agent", "base", "army", "episode", "seed", "destruction", "stars", "three_star", "steps"])
        ew.writeheader()
        ew.writerows(all_rows)
    print(f"Wrote raw episodes to {raw_episodes_csv}")

    # 5. Bootstrap CI across the 16 independent (base, army) pairs
    print("\n" + "=" * 90)
    print("STEP 2: SUMMARY ACROSS 16 INDEPENDENT PAIRS (BOOTSTRAP 95% CONFIDENCE INTERVALS)")
    print("=" * 90)
    print(f"{'Agent':<15} {'Mean Dest % [95% CI]':>26} {'Mean Stars [95% CI]':>22} {'3-Star Rate % [95% CI]':>25}")
    print("-" * 92)

    summary_stats = {}
    for ag in agents_order:
        dm, dl, dh = _bootstrap_ci(pair_stats[ag]["dest"])
        sm, sl, sh = _bootstrap_ci(pair_stats[ag]["stars"])
        tm, tl, th = _bootstrap_ci(pair_stats[ag]["three"])
        summary_stats[ag] = {
            "dest_mean": dm, "dest_lo": dl, "dest_hi": dh,
            "stars_mean": sm, "stars_lo": sl, "stars_hi": sh,
            "three_mean": tm, "three_lo": tl, "three_hi": th,
        }
        print(f"{ag:<15} {dm:6.2f}% [{dl:5.2f}, {dh:5.2f}]   {sm:4.2f} [{sl:4.2f}, {sh:4.2f}]   {tm:6.2f}% [{tl:5.2f}, {th:5.2f}]")

    # 6. Paired Comparison: PPO vs Best Baseline
    print("\n" + "=" * 90)
    print("STEP 3: PAIRED DIFFERENCE (PPO vs BASELINES)")
    print("=" * 90)
    best_dest_base = max(baseline_strategies, key=lambda s: summary_stats[s]["dest_mean"])
    best_star_base = max(baseline_strategies, key=lambda s: summary_stats[s]["stars_mean"])

    dd_m, dd_l, dd_h = _bootstrap_ci(pair_stats["maskable_ppo"]["dest"] - pair_stats[best_dest_base]["dest"])
    ds_m, ds_l, ds_h = _bootstrap_ci(pair_stats["maskable_ppo"]["stars"] - pair_stats[best_star_base]["stars"])

    beats_dest = summary_stats["maskable_ppo"]["dest_mean"] > summary_stats[best_dest_base]["dest_mean"]
    beats_stars = summary_stats["maskable_ppo"]["stars_mean"] > summary_stats[best_star_base]["stars_mean"]
    beats_random = summary_stats["maskable_ppo"]["dest_mean"] > summary_stats["random_masked"]["dest_mean"]

    print(f"Best baseline on destruction: {best_dest_base} ({summary_stats[best_dest_base]['dest_mean']:.2f}%)")
    print(f"Best baseline on stars:       {best_star_base} ({summary_stats[best_star_base]['stars_mean']:.2f})")
    print(f"Paired delta (PPO - {best_dest_base}) destruction: {dd_m:+.2f} pp [95% CI {dd_l:+.2f}, {dd_h:+.2f}]")
    print(f"Paired delta (PPO - {best_star_base}) stars:       {ds_m:+.3f} [95% CI {ds_l:+.3f}, {ds_h:+.3f}]")

    print("\n--- FINAL CONCLUSION ---")
    print(f"Does MaskablePPO beat random_masked on destruction? {'YES' if beats_random else 'NO'}")
    print(f"Does MaskablePPO beat best baseline on destruction? {'YES' if beats_dest else 'NO'} ({summary_stats['maskable_ppo']['dest_mean']:.2f}% vs {summary_stats[best_dest_base]['dest_mean']:.2f}%)")
    print(f"Does MaskablePPO beat best baseline on stars?       {'YES' if beats_stars else 'NO'} ({summary_stats['maskable_ppo']['stars_mean']:.2f} vs {summary_stats[best_star_base]['stars_mean']:.2f})")

    return summary_stats, variance_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    run_evaluation(episodes=args.episodes, workers=args.workers)
