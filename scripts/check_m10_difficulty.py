"""M10 Step 1c: Difficulty Check.

Runs left_wave, smart_funnel, and surround on 40 train layouts x 7 armies x 10 episodes.
Reports destruction distribution and checks if >80% of layouts are degenerate (all-0% or all-100%).
"""

import csv
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents import STRATEGIES
from sim.env import CoCEnv

DATA_DIR = ROOT / "data"
TRAIN_DIR = DATA_DIR / "bases_gen" / "train"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

ARMIES = [
    "giant_barch",
    "barch",
    "goblin_giant",
    "mixed_wb",
    "mass_dragons",
    "gowiva",
    "hog_rush",
]




def _eval_combo(args: tuple[str, str, str, int]) -> dict[str, Any]:
    strat_name, base_path_str, army_name, n_episodes = args
    strat_fn = STRATEGIES[strat_name]
    env = CoCEnv(base_file=base_path_str, army=army_name)

    dests = []
    stars = []
    th_kills = []

    for ep in range(n_episodes):
        obs, info = env.reset(seed=ep)
        done = False
        step_idx = 0
        while not done:
            action = strat_fn(env, step_idx)
            obs, reward, term, trunc, info = env.step(action)
            done = term or trunc
            step_idx += 1

        dests.append(float(info.get("destruction", 0.0)) * 100.0)
        stars.append(int(info.get("stars", 0)))
        th_kills.append(1 if getattr(env, "th_destroyed", False) else 0)

    return {
        "strategy": strat_name,
        "base": Path(base_path_str).name,
        "army": army_name,
        "episodes": n_episodes,
        "mean_dest": float(np.mean(dests)),
        "std_dest": float(np.std(dests)),
        "min_dest": float(np.min(dests)),
        "max_dest": float(np.max(dests)),
        "mean_stars": float(np.mean(stars)),
        "th_kill_rate": float(np.mean(th_kills)),
    }


def main():
    print("=" * 80)
    print("M10 STEP 1c: BASELINE DIFFICULTY CHECK ON 40 TRAIN LAYOUTS")
    print("=" * 80)

    # 40 train layouts (seeds 0..39)
    train_layouts = sorted(TRAIN_DIR.glob("gen_base_*.json"))[:40]
    print(f"Testing {len(train_layouts)} train layouts across {len(ARMIES)} armies and {len(STRATEGIES)} strategies.")
    print(f"Total combinations: {len(train_layouts)} x {len(ARMIES)} x {len(STRATEGIES)} = {len(train_layouts)*len(ARMIES)*len(STRATEGIES)}")
    print(f"Total episodes: {len(train_layouts)*len(ARMIES)*len(STRATEGIES)*10:,} (10 episodes per combo)")

    tasks = []
    for strat in STRATEGIES:
        for layout_path in train_layouts:
            for army in ARMIES:
                tasks.append((strat, str(layout_path), army, 10))

    t0 = time.perf_counter()
    workers = min(6, os.cpu_count() or 4)
    print(f"Running on {workers} parallel worker processes...", flush=True)

    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, res in enumerate(pool.map(_eval_combo, tasks, chunksize=10)):
            results.append(res)
            if (i + 1) % 100 == 0 or (i + 1) == len(tasks):
                elapsed = time.perf_counter() - t0
                print(f"  Completed {i + 1}/{len(tasks)} combos in {elapsed:.1f}s ({elapsed/(i+1):.2f}s/combo)", flush=True)

    dur = time.perf_counter() - t0
    print(f"\nAll {len(tasks)} combinations completed in {dur:.1f}s.")

    # Save to CSV
    csv_path = RESULTS_DIR / "m10_difficulty_check.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved results to {csv_path}")

    # Analyze per-layout degeneracy
    # "If more than 80% of layouts are all-0% or all-100% for every strategy, adjust generator"
    layout_stats: dict[str, list[float]] = {}
    for r in results:
        base_name = r["base"]
        layout_stats.setdefault(base_name, []).append(r["mean_dest"])

    degenerate_count = 0
    total_layouts = len(layout_stats)

    print("\n--- Per-Layout Summary (Mean Destruction Across 21 Combos: 3 strats x 7 armies) ---")
    for base_name, dests in sorted(layout_stats.items()):
        mean_d = float(np.mean(dests))
        min_d = float(np.min(dests))
        max_d = float(np.max(dests))
        # A layout is degenerate if all evaluations are 0% or all evaluations are 100%
        is_all_zero = (max_d <= 0.01)
        is_all_hundred = (min_d >= 99.99)
        is_degen = is_all_zero or is_all_hundred
        if is_degen:
            degenerate_count += 1
        degen_flag = " [DEGENERATE]" if is_degen else ""
        print(f"  {base_name}: mean={mean_d:5.1f}% [min={min_d:5.1f}%, max={max_d:5.1f}%]{degen_flag}")

    degen_rate = (degenerate_count / total_layouts) * 100.0
    print(f"\nDegeneracy Audit:")
    print(f"  Total Layouts Evaluated: {total_layouts}")
    print(f"  Degenerate Layouts (all-0% or all-100% across all strategies & armies): {degenerate_count} ({degen_rate:.1f}%)")
    print(f"  Non-Degenerate Layouts: {total_layouts - degenerate_count} ({100.0 - degen_rate:.1f}%)")

    # Overall strategy destruction distributions
    print("\n--- Strategy Aggregate Destruction % on 40 Train Layouts ---")
    for strat in STRATEGIES:
        strat_dests = [r["mean_dest"] for r in results if r["strategy"] == strat]
        strat_stars = [r["mean_stars"] for r in results if r["strategy"] == strat]
        strat_th = [r["th_kill_rate"] * 100.0 for r in results if r["strategy"] == strat]
        print(f"  {strat:15s}: Dest = {np.mean(strat_dests):5.2f}% (std={np.std(strat_dests):.1f}%), Stars = {np.mean(strat_stars):.2f}, TH-Kill = {np.mean(strat_th):.1f}%")

    if degen_rate > 80.0:
        print(f"\nFAILURE: Degenerate rate {degen_rate:.1f}% exceeds 80% threshold!")
        sys.exit(1)
    else:
        print(f"\n>>> DIFFICULTY CHECK PASSED: Degenerate rate {degen_rate:.1f}% is well below the 80% threshold.")


if __name__ == "__main__":
    main()
