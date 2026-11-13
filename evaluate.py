"""Evaluate rule-based baseline strategies across all bases and TH8 armies."""
import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from agents import STRATEGIES
from sim import CoCEnv

DATA_DIR = Path(__file__).resolve().parent / "data"
BASES_DIR = DATA_DIR / "bases"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _army_names() -> list[str]:
    raw = json.loads((DATA_DIR / "armies.json").read_text(encoding="utf-8"))
    return [k for k in raw if not k.startswith("_")]


def _run_combo(task: tuple[str, str, str, int]) -> list[dict]:
    strategy_name, base_file, army_name, episodes = task
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
            "strategy": strategy_name,
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


def evaluate_base(base_file: str, army_name: str | None = None, episodes: int = 20, strategy: str = "left_wave"):
    army = army_name or _army_names()[0]
    rows = _run_combo((strategy, base_file, army, episodes))
    d = [r["destruction"] for r in rows]
    s = [r["stars"] for r in rows]
    return float(np.mean(d)), float(np.mean(s))


def run_baselines(
    episodes: int = 100,
    output_csv: Path = RESULTS_DIR / "baselines.csv",
    workers: int | None = None,
) -> tuple[list[dict], str]:
    bases = [p.name for p in sorted(BASES_DIR.glob("*.json"))]
    armies = _army_names()
    strategies = list(STRATEGIES.keys())
    tasks = [(s, b, a, episodes) for s in strategies for b in bases for a in armies]

    t0 = time.perf_counter()
    max_workers = workers if workers is not None else min(len(tasks), max(1, os.cpu_count() or 1))
    all_rows: list[dict] = []
    if max_workers <= 1:
        for idx, t in enumerate(tasks, 1):
            all_rows.extend(_run_combo(t))
            if idx % 12 == 0 or idx == len(tasks):
                print(f"[{idx}/{len(tasks)}] {t[0]} / {t[1]} / {t[2]} ({time.perf_counter() - t0:.1f}s)", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for idx, rows in enumerate(pool.map(_run_combo, tasks), 1):
                all_rows.extend(rows)
                if idx % 12 == 0 or idx == len(tasks):
                    t = tasks[idx - 1]
                    print(f"[{idx}/{len(tasks)}] {t[0]} / {t[1]} / {t[2]} ({time.perf_counter() - t0:.1f}s)", flush=True)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["strategy", "base", "army", "episode", "seed", "destruction", "stars", "three_star", "steps"]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    m5b_csv = RESULTS_DIR / "baselines_m5b.csv"
    if output_csv.resolve() != m5b_csv.resolve():
        with m5b_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} episodes to {output_csv} in {time.perf_counter() - t0:.1f}s")
    print(f"\n{'Strategy':<14} {'Base':<14} {'Army':<14} {'Mean Dest':>10} {'3-Star':>9}")
    print("-" * 65)
    for s in strategies:
        for b in bases:
            for a in armies:
                sub = [r for r in all_rows if r["strategy"] == s and r["base"] == b and r["army"] == a]
                md = float(np.mean([r["destruction"] for r in sub])) * 100.0
                r3 = float(np.mean([r["three_star"] for r in sub])) * 100.0
                print(f"{s:<14} {b:<14} {a:<14} {md:>9.1f}% {r3:>8.1f}%")

    print("\n=== Strategy Summary ===")
    print(f"{'Strategy':<14} {'Episodes':>9} {'Mean Dest %':>12} {'3-Star Rate':>12} {'Mean Stars':>11}")
    print("-" * 62)
    best_name, best_dest = "", -1.0
    for s in strategies:
        sub = [r for r in all_rows if r["strategy"] == s]
        md = float(np.mean([r["destruction"] for r in sub])) * 100.0
        r3 = float(np.mean([r["three_star"] for r in sub])) * 100.0
        ms = float(np.mean([r["stars"] for r in sub]))
        print(f"{s:<14} {len(sub):>9d} {md:>11.2f}% {r3:>11.2f}% {ms:>11.2f}")
        if md > best_dest:
            best_dest = md
            best_name = s

    print(f"\nBest baseline: {best_name} (mean destruction = {best_dest:.2f}%)")
    return all_rows, best_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate baseline strategies on all bases and armies.")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "baselines.csv")
    args = parser.parse_args()
    run_baselines(episodes=args.episodes, output_csv=args.output, workers=args.workers)
