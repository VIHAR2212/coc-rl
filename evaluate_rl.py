"""Evaluate trained MaskablePPO vs best M6 baseline vs random masked agent on held-out bases."""
import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from agents import STRATEGIES
from sim import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv, HELD_OUT_BASES

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _army_names() -> list[str]:
    raw = json.loads((DATA_DIR / "armies.json").read_text(encoding="utf-8"))
    return [k for k in raw if not k.startswith("_")]


def _run_rl_task(args: tuple[str, str, str, str, int]) -> list[dict]:
    agent_name, model_path, base_file, army_name, episodes = args
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army_name])
    model = MaskablePPO.load(model_path, device="cpu") if agent_name == "maskable_ppo" else None
    rows: list[dict] = []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep, options={"base_file": base_file, "army": army_name})
        rng = np.random.default_rng(ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}
        while not done:
            mask = env.action_masks()
            if agent_name == "maskable_ppo":
                action, _ = model.predict(obs, deterministic=True, action_masks=mask)
                act = int(action)
            else:
                valid = np.flatnonzero(mask)
                act = int(rng.choice(valid))
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
    return rows


def _run_baseline_task(args: tuple[str, str, str, int]) -> list[dict]:
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


def evaluate_held_out(
    model_path: Path = Path("models/ppo_coc_v1.zip"),
    best_baseline: str = "left_wave",
    episodes: int = 100,
    output_csv: Path = RESULTS_DIR / "rl_vs_baselines.csv",
    workers: int | None = None,
) -> dict[str, dict[str, float]]:
    armies = _army_names()
    bases = list(HELD_OUT_BASES)
    max_workers = workers if workers is not None else max(1, os.cpu_count() or 1)
    t0 = time.perf_counter()

    rl_tasks = [
        (agent, str(model_path), b, a, episodes)
        for agent in ("maskable_ppo", "random_masked")
        for b in bases
        for a in armies
    ]
    base_tasks = [(best_baseline, b, a, episodes) for b in bases for a in armies]

    all_rows: list[dict] = []
    if max_workers <= 1:
        for t in rl_tasks:
            all_rows.extend(_run_rl_task(t))
        for t in base_tasks:
            all_rows.extend(_run_baseline_task(t))
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for rows in pool.map(_run_rl_task, rl_tasks):
                all_rows.extend(rows)
            for rows in pool.map(_run_baseline_task, base_tasks):
                all_rows.extend(rows)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["agent", "base", "army", "episode", "seed", "destruction", "stars", "three_star", "steps"]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    agents_order = ["maskable_ppo", best_baseline, "random_masked"]
    print(f"\nHeld-out bases {bases}, {episodes} episodes/(base, army), {time.perf_counter() - t0:.1f}s")
    print(f"\n{'Agent':<16} {'Base':<12} {'Army':<14} {'Mean Dest %':>11} {'3-Star %':>9}")
    print("-" * 66)
    for ag in agents_order:
        for b in bases:
            for a in armies:
                sub = [r for r in all_rows if r["agent"] == ag and r["base"] == b and r["army"] == a]
                md = float(np.mean([r["destruction"] for r in sub])) * 100.0
                r3 = float(np.mean([r["three_star"] for r in sub])) * 100.0
                print(f"{ag:<16} {b:<12} {a:<14} {md:>10.2f}% {r3:>8.2f}%")

    print("\n=== Held-Out Summary ===")
    print(f"{'Agent':<16} {'Episodes':>9} {'Mean Dest %':>12} {'3-Star Rate':>12} {'Mean Stars':>11}")
    print("-" * 64)
    summary: dict[str, dict[str, float]] = {}
    for ag in agents_order:
        sub = [r for r in all_rows if r["agent"] == ag]
        md = float(np.mean([r["destruction"] for r in sub])) * 100.0
        r3 = float(np.mean([r["three_star"] for r in sub])) * 100.0
        ms = float(np.mean([r["stars"] for r in sub]))
        summary[ag] = {"mean_dest": md, "three_star_rate": r3, "mean_stars": ms}
        print(f"{ag:<16} {len(sub):>9d} {md:>11.2f}% {r3:>11.2f}% {ms:>11.2f}")

    beats_random = summary["maskable_ppo"]["mean_dest"] > summary["random_masked"]["mean_dest"]
    beats_baseline = summary["maskable_ppo"]["mean_dest"] > summary[best_baseline]["mean_dest"]
    print(f"\nSaved -> {output_csv}")
    print(f"PASS check: beats_random={beats_random}, beats_best_baseline={beats_baseline}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate trained MaskablePPO on held-out bases.")
    parser.add_argument("--model", type=Path, default=Path("models/ppo_coc_v1.zip"))
    parser.add_argument("--baseline", type=str, default="left_wave")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "rl_vs_baselines.csv")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    evaluate_held_out(
        model_path=args.model,
        best_baseline=args.baseline,
        episodes=args.episodes,
        output_csv=args.output,
        workers=args.workers,
    )

