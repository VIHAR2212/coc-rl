"""Evaluate all 3 baselines, random_masked, and multi-seed MaskablePPO on held-out bases."""
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


def _run_rl_task(args: tuple[str, list[str], str, str, int]) -> list[dict]:
    agent_name, model_paths, base_file, army_name, episodes = args
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army_name])
    models = [MaskablePPO.load(p, device="cpu") for p in model_paths] if agent_name == "maskable_ppo" else []
    rows: list[dict] = []
    for ep in range(episodes):
        obs, _ = env.reset(seed=ep, options={"base_file": base_file, "army": army_name})
        rng = np.random.default_rng(ep)
        model = models[ep % len(models)] if models else None
        model_tag = Path(model_paths[ep % len(models)]).stem if models else agent_name
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
            "model_tag": model_tag,
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
            "model_tag": strategy_name,
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


def _bootstrap_ci(pair_vals: np.ndarray, n_boot: int = 10_000, seed: int = 0) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) across independent (base, army) pairs."""
    rng = np.random.default_rng(seed)
    n = len(pair_vals)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = pair_vals[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(pair_vals.mean()), float(lo), float(hi)


def evaluate_held_out(
    model_paths: list[Path] | None = None,
    episodes: int = 100,
    output_csv: Path = RESULTS_DIR / "rl_vs_baselines.csv",
    pairs_csv: Path = RESULTS_DIR / "rl_vs_baselines_pairs.csv",
    workers: int | None = None,
) -> dict[str, dict[str, float]]:
    if model_paths is None:
        candidates = sorted(Path("models").glob("ppo_m7b_seed*.zip"))
        model_paths = candidates or [Path("models/ppo_coc_v1.zip")]
    armies = _army_names()
    bases = list(HELD_OUT_BASES)
    max_workers = workers if workers is not None else max(1, os.cpu_count() or 1)
    t0 = time.perf_counter()

    baseline_names = list(STRATEGIES.keys())
    str_paths = [str(p) for p in model_paths]
    rl_tasks = [
        (agent, str_paths if agent == "maskable_ppo" else [], b, a, episodes)
        for agent in ("maskable_ppo", "random_masked")
        for b in bases
        for a in armies
    ]
    base_tasks = [(s, b, a, episodes) for s in baseline_names for b in bases for a in armies]

    all_rows: list[dict] = []
    if max_workers <= 1:
        for t in base_tasks:
            all_rows.extend(_run_baseline_task(t))
        for t in rl_tasks:
            all_rows.extend(_run_rl_task(t))
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for rows in pool.map(_run_baseline_task, base_tasks):
                all_rows.extend(rows)
            for rows in pool.map(_run_rl_task, rl_tasks):
                all_rows.extend(rows)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["agent", "model_tag", "base", "army", "episode", "seed", "destruction", "stars", "three_star", "steps"]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    agents_order = [*baseline_names, "random_masked", "maskable_ppo"]
    pairs = [(b, a) for b in bases for a in armies]
    pair_rows: list[dict] = []
    pair_stats: dict[str, dict[str, np.ndarray]] = {
        ag: {"dest": np.zeros(len(pairs)), "stars": np.zeros(len(pairs)), "three": np.zeros(len(pairs))}
        for ag in agents_order
    }

    print(
        f"\nHeld-out bases ({len(bases)}): {bases} | {len(pairs)} (base, army) pairs | "
        f"{episodes} seeded episodes/pair | {time.perf_counter() - t0:.1f}s"
    )
    print(f"PPO models evaluated: {[p.name for p in model_paths]}")
    print(f"\n{'Agent':<14} {'Base':<12} {'Army':<14} {'Dest % (SD)':>15} {'Stars':>7} {'3-Star %':>9}")
    print("-" * 76)
    for ag in agents_order:
        nonzero_var = 0
        for p_idx, (b, a) in enumerate(pairs):
            sub = [r for r in all_rows if r["agent"] == ag and r["base"] == b and r["army"] == a]
            ds = np.array([r["destruction"] for r in sub], dtype=np.float64) * 100.0
            ss = np.array([r["stars"] for r in sub], dtype=np.float64)
            t3 = np.array([r["three_star"] for r in sub], dtype=np.float64) * 100.0
            md, sd = float(ds.mean()), float(ds.std())
            ms, m3 = float(ss.mean()), float(t3.mean())
            if sd > 1e-6:
                nonzero_var += 1
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
                "mean_stars": round(ms, 4),
                "three_star_pct": round(m3, 4),
            })
            print(f"{ag:<14} {b:<12} {a:<14} {md:>6.2f}% ({sd:4.2f}) {ms:>7.2f} {m3:>8.2f}%")
        print(f"  [{ag}] pairs with nonzero seed variance: {nonzero_var}/{len(pairs)}")

    with pairs_csv.open("w", newline="", encoding="utf-8") as f:
        pw = csv.DictWriter(
            f,
            fieldnames=["agent", "base", "army", "episodes", "mean_dest_pct", "std_dest_pct", "mean_stars", "three_star_pct"],
        )
        pw.writeheader()
        pw.writerows(pair_rows)

    print(f"\n=== Held-Out Summary Across {len(pairs)} Independent (Base, Army) Pairs (95% Pair Bootstrap CI) ===")
    print(f"{'Agent':<14} {'Dest % [95% CI]':>24} {'Stars [95% CI]':>22} {'3-Star % [95% CI]':>24}")
    print("-" * 88)
    summary: dict[str, dict[str, float]] = {}
    for ag in agents_order:
        dm, dl, dh = _bootstrap_ci(pair_stats[ag]["dest"])
        sm, sl, sh = _bootstrap_ci(pair_stats[ag]["stars"])
        tm, tl, th = _bootstrap_ci(pair_stats[ag]["three"])
        summary[ag] = {
            "mean_dest": dm, "dest_ci_lo": dl, "dest_ci_hi": dh,
            "mean_stars": sm, "stars_ci_lo": sl, "stars_ci_hi": sh,
            "three_star_rate": tm, "three_ci_lo": tl, "three_ci_hi": th,
        }
        print(
            f"{ag:<14} {dm:6.2f}% [{dl:5.2f}, {dh:5.2f}]   "
            f"{sm:4.2f} [{sl:4.2f}, {sh:4.2f}]   "
            f"{tm:6.2f}% [{tl:5.2f}, {th:5.2f}]"
        )

    if len(model_paths) > 1:
        print("\n=== Per-Seed MaskablePPO Held-Out Breakdown ===")
        for p in model_paths:
            tag = p.stem
            sub = [r for r in all_rows if r["agent"] == "maskable_ppo" and r["model_tag"] == tag]
            if sub:
                print(
                    f"  {tag}: mean_dest={np.mean([r['destruction'] for r in sub])*100:.2f}%, "
                    f"mean_stars={np.mean([r['stars'] for r in sub]):.2f}, "
                    f"3-star={np.mean([r['three_star'] for r in sub])*100:.2f}% (n={len(sub)})"
                )

    best_dest_base = max(baseline_names, key=lambda s: summary[s]["mean_dest"])
    best_star_base = max(baseline_names, key=lambda s: summary[s]["mean_stars"])
    dd_m, dd_l, dd_h = _bootstrap_ci(pair_stats["maskable_ppo"]["dest"] - pair_stats[best_dest_base]["dest"])
    ds_m, ds_l, ds_h = _bootstrap_ci(pair_stats["maskable_ppo"]["stars"] - pair_stats[best_star_base]["stars"])
    beats_dest = summary["maskable_ppo"]["mean_dest"] > summary[best_dest_base]["mean_dest"]
    beats_stars = summary["maskable_ppo"]["mean_stars"] > summary[best_star_base]["mean_stars"]
    beats_random = summary["maskable_ppo"]["mean_dest"] > summary["random_masked"]["mean_dest"]

    print(f"\nBest baseline on destruction: {best_dest_base} ({summary[best_dest_base]['mean_dest']:.2f}%)")
    print(f"Best baseline on stars:       {best_star_base} ({summary[best_star_base]['mean_stars']:.2f})")
    print(f"Paired delta (PPO - {best_dest_base}) dest:  {dd_m:+.2f} pp [95% CI {dd_l:+.2f}, {dd_h:+.2f}]")
    print(f"Paired delta (PPO - {best_star_base}) stars: {ds_m:+.3f} [95% CI {ds_l:+.3f}, {ds_h:+.3f}]")
    print(f"Saved -> {output_csv} and {pairs_csv}")
    print(f"CHECK: beats_random={beats_random}, beats_best_dest={beats_dest}, beats_best_stars={beats_stars}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate baselines, random_masked, and MaskablePPO on held-out bases.")
    parser.add_argument("--models", type=Path, nargs="+", default=None)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "rl_vs_baselines.csv")
    parser.add_argument("--pairs-output", type=Path, default=RESULTS_DIR / "rl_vs_baselines_pairs.csv")
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    evaluate_held_out(
        model_paths=args.models,
        episodes=args.episodes,
        output_csv=args.output,
        pairs_csv=args.pairs_output,
        workers=args.workers,
    )
