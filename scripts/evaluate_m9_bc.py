"""Evaluate Behavior Cloning (BC) policies on held-out bases (base07 to base10).

M9 Step 2c:
- Evaluates left_wave baseline and 3 BC models (seed 42, 43, 44) on all 28 held-out pairs:
  4 held-out bases (base07..base10) x 7 TH8 armies, 100 episodes per pair (seeds 0..99).
- Evaluates both deterministic and stochastic policy actions.
- Computes 3-seed aggregates for both deterministic and stochastic modes.
- Computes paired bootstrap 95% confidence intervals against left_wave.
- Saves results to results/m9_bc.csv and results/m9_bc_summary.csv.
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
EPISODES_PER_PAIR = 100
BC_SEEDS = [42, 43, 44]
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


def _eval_bc_pair(args):
    model_path_str, deterministic, base_file, army_name, episodes = args
    from sb3_contrib import MaskablePPO

    model_path = Path(model_path_str)
    model = MaskablePPO.load(model_path, device="cpu")
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army_name], shaping_mode="stars_aware")

    dests, stars, three_stars, th_kills, cross_50s = [], [], [], [], []

    mode_str = "det" if deterministic else "stoch"
    agent_name = f"{model_path.stem}_{mode_str}"

    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}

        while not done:
            mask = env.action_masks()
            act, _ = model.predict(obs, action_masks=mask, deterministic=deterministic)
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
        "agent": agent_name,
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


def main(workers: int = 2):
    t0 = time.perf_counter()
    pairs = [(b, a) for b in HELD_OUT_BASES for a in DEFAULT_ARMIES]
    print("=" * 80)
    print("M9 STEP 2c: BEHAVIOR CLONING HELD-OUT EVALUATION (28 PAIRS, 100 SEEDS)")
    print(f"Bases: {HELD_OUT_BASES}")
    print(f"Armies: {DEFAULT_ARMIES}")
    print(f"Total pairs: {len(pairs)} | Episodes per pair: {EPISODES_PER_PAIR} | Workers: {workers}")
    print("=" * 80, flush=True)

    # 1. Evaluate left_wave
    lw_tasks = [(b, a, EPISODES_PER_PAIR) for b, a in pairs]
    print(f"\n--- 1. Evaluating left_wave ({len(lw_tasks)} tasks) ---", flush=True)
    lw_rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_left_wave_pair, lw_tasks), 1):
            lw_rows.append(res)
            if idx % 7 == 0 or idx == len(lw_tasks):
                print(f"  [{idx}/{len(lw_tasks)}] left_wave | {res['base']} | {res['army']} ({time.perf_counter() - t0:.1f}s)", flush=True)

    # 2. Evaluate BC models (seeds 42, 43, 44) x (deterministic, stochastic)
    bc_models = [ROOT / "models" / f"ppo_m9_bc_seed{s}.zip" for s in BC_SEEDS]
    for p in bc_models:
        if not p.exists():
            raise FileNotFoundError(f"Model {p} not found! Run scripts/train_m9_bc.py first.")

    bc_tasks = []
    for model_path in bc_models:
        for det in [True, False]:
            for b, a in pairs:
                bc_tasks.append((str(model_path), det, b, a, EPISODES_PER_PAIR))

    print(f"\n--- 2. Evaluating BC policies ({len(bc_tasks)} tasks) ---", flush=True)
    bc_rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_bc_pair, bc_tasks), 1):
            bc_rows.append(res)
            if idx % 14 == 0 or idx == len(bc_tasks):
                print(f"  [{idx}/{len(bc_tasks)}] {res['agent']} | {res['base']} | {res['army']} ({time.perf_counter() - t0:.1f}s)", flush=True)

    # 3. Build 3-seed aggregates for deterministic and stochastic
    agg_rows = []
    for mode_str in ["det", "stoch"]:
        agg_label = f"ppo_m9_bc_3seed_{mode_str}"
        for b, a in pairs:
            seed_rows = [r for r in bc_rows if r["agent"].endswith(f"_{mode_str}") and r["base"] == b and r["army"] == a]
            agg_rows.append(_condense_seed_rows(seed_rows, agg_label))

    all_rows = lw_rows + bc_rows + agg_rows

    # Save detailed per-pair CSV
    out_csv = RESULTS_DIR / "m9_bc.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in all_rows:
            writer.writerow({k: r[k] for k in FIELDS})
    print(f"\nSaved per-pair results to {out_csv}", flush=True)

    # 4. Compute Summary Table with paired bootstrap 95% CIs vs left_wave
    lw_by_pair = {(r["base"], r["army"]): r for r in lw_rows}

    agent_names = [
        "left_wave",
        "ppo_m9_bc_seed42_det",
        "ppo_m9_bc_seed43_det",
        "ppo_m9_bc_seed44_det",
        "ppo_m9_bc_3seed_det",
        "ppo_m9_bc_seed42_stoch",
        "ppo_m9_bc_seed43_stoch",
        "ppo_m9_bc_seed44_stoch",
        "ppo_m9_bc_3seed_stoch",
    ]

    print("\n" + "=" * 120)
    print("M9 STEP 2c SUMMARY: BEHAVIOR CLONING ON 28 HELD-OUT PAIRS (with 95% paired bootstrap CIs vs left_wave)")
    print("=" * 120)
    print(
        f"{'Agent':<26} {'Dest % [95% CI]':<22} {'Stars [95% CI]':<18} "
        f"{'3-Star %':<10} {'TH-Kill %':<11} {'>=50% %':<10} {'dDest vs LW [95% CI]':<22} {'dStars vs LW [95% CI]':<20}"
    )
    print("-" * 120)

    summary_rows = []
    for name in agent_names:
        rows = [r for r in all_rows if r["agent"] == name]
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
            f"{name:<26} {dest_str:<22} {star_str:<18} {tm:5.1f}%     {thm:5.1f}%      {cm:5.1f}%     {dd_str:<22} {ds_str:<20}"
        )

        summary_rows.append({
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

    sum_csv = RESULTS_DIR / "m9_bc_summary.csv"
    with sum_csv.open("w", newline="", encoding="utf-8") as f:
        sum_fields = list(summary_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=sum_fields)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\nSaved summary to {sum_csv}", flush=True)
    print(f"Total time elapsed: {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()

