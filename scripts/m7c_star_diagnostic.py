"""M7c star-gap diagnostic: why does Part B PPO trail left_wave on stars?

For the 16 ground-army pairs (base07..10 x giant_barch/barch/goblin_giant/mixed_wb)
where the stars gap exists, record per episode:
  - destruction %, stars, three_star
  - whether the Town Hall died (info["th_destroyed"])
  - whether destruction reached 50%
Then report per (agent, base, army): TH-kill rate, 50%-crossing rate, 3-star rate,
and destruction conditional on not three-starring.

Agents: left_wave, the 3 Part B seeds and the 3 no-anti-collapse ablation seeds.
Saves results/m7c_star_diagnostic.csv. Evaluation only - no training.
"""
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents import STRATEGIES  # noqa: E402
from sim import CoCEnv  # noqa: E402
from sim.rl_wrapper import ActionMaskCoCEnv  # noqa: E402

BASES = ["base07.json", "base08.json", "base09.json", "base10.json"]
ARMIES = ["giant_barch", "barch", "goblin_giant", "mixed_wb"]
EPISODES = 50
MODELS = [f"models/ppo_m7b_seed{s}.zip" for s in (42, 43, 44)] + \
         [f"models/ppo_m7c_noac_seed{s}.zip" for s in (42, 43, 44)]
RESULTS = ROOT / "results"


def _label(model_path: str) -> str:
    stem = Path(model_path).stem
    if stem.startswith("ppo_m7b_seed"):
        return f"maskable_ppo_partB_seed{stem.split('seed')[1]}"
    return f"maskable_ppo_noac_seed{stem.split('seed')[1]}"


def _eval_baseline(args):
    strategy, base, army = args
    env = CoCEnv(base_file=base, army=army)
    dests, stars, th, cross = [], [], [], []
    for ep in range(EPISODES):
        env.reset(seed=ep)
        done, step_idx, info = False, 0, {"destruction": 0.0, "stars": 0}
        while not done:
            _, _, term, trunc, info = env.step(STRATEGIES[strategy](env, step_idx))
            done = term or trunc
            step_idx += 1
        th_hit = bool(env.th_destroyed)
        d = float(info["destruction"])
        dests.append(d)
        stars.append(int(info["stars"]))
        th.append(int(th_hit))
        cross.append(int(d >= 0.5))
    return _row(strategy, base, army, dests, stars, th, cross)


def _eval_ppo(args):
    model_path, base, army = args
    from sb3_contrib import MaskablePPO
    model = MaskablePPO.load(model_path, device="cpu")
    env = ActionMaskCoCEnv(bases=[base], armies=[army], shaping_mode="stars_aware")
    dests, stars, th, cross = [], [], [], []
    for ep in range(EPISODES):
        obs, _ = env.reset(seed=ep)
        done, info = False, {"destruction": 0.0, "stars": 0, "th_destroyed": 0}
        th_hit = False
        while not done:
            act, _ = model.predict(obs, action_masks=env.action_masks(), deterministic=True)
            obs, _, term, trunc, info = env.step(int(act))
            th_hit = th_hit or bool(info.get("th_destroyed", 0))
            done = term or trunc
        d = float(info["destruction"])
        dests.append(d)
        stars.append(int(info["stars"]))
        th.append(int(th_hit))
        cross.append(int(d >= 0.5))
    return _row(_label(model_path), base, army, dests, stars, th, cross)


def _row(agent, base, army, dests, stars, th, cross):
    non3 = [d * 100 for d, s in zip(dests, stars) if s < 3]
    return {
        "agent": agent,
        "base": base,
        "army": army,
        "episodes": EPISODES,
        "mean_dest_pct": round(float(np.mean(dests)) * 100, 2),
        "mean_stars": round(float(np.mean(stars)), 3),
        "three_star_pct": round(float(np.mean([s == 3 for s in stars])) * 100, 2),
        "th_kill_pct": round(float(np.mean(th)) * 100, 2),
        "cross_50_pct": round(float(np.mean(cross)) * 100, 2),
        "dest_pct_when_not_3star": round(float(np.mean(non3)), 2) if non3 else None,
    }


def main(workers: int = 2) -> None:
    t0 = time.perf_counter()
    base_tasks = [("left_wave", b, a) for b in BASES for a in ARMIES]
    ppo_tasks = [(m, b, a) for m in MODELS for b in BASES for a in ARMIES]
    rows = []
    print(f"=== M7c star-gap diagnostic ===\nPairs: {len(BASES) * len(ARMIES)} | episodes/pair: {EPISODES}\n"
          f"PPO models: {[Path(m).name for m in MODELS]}", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, r in enumerate(pool.map(_eval_baseline, base_tasks), 1):
            rows.append(r)
            print(f"[baseline {i}/{len(base_tasks)}] {r['agent']} / {r['base']} / {r['army']} "
                  f"({time.perf_counter() - t0:.0f}s)", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, r in enumerate(pool.map(_eval_ppo, ppo_tasks), 1):
            rows.append(r)
            if i % 8 == 0 or i == len(ppo_tasks):
                print(f"[ppo {i}/{len(ppo_tasks)}] {r['agent']} / {r['base']} / {r['army']} "
                      f"({time.perf_counter() - t0:.0f}s)", flush=True)

    out = RESULTS / "m7c_star_diagnostic.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\n=== AGGREGATED OVER 16 GROUND-ARMY PAIRS ===")
    print(f"{'Agent':<30} {'Dest%':>7} {'Stars':>6} {'3star%':>7} {'TH kill%':>9} {'>=50%':>7} {'Dest|non3*':>11}")
    for agent in ["left_wave"] + [_label(m) for m in MODELS]:
        sub = [r for r in rows if r["agent"] == agent]
        print(f"{agent:<30} {np.mean([r['mean_dest_pct'] for r in sub]):7.2f} "
              f"{np.mean([r['mean_stars'] for r in sub]):6.2f} "
              f"{np.mean([r['three_star_pct'] for r in sub]):7.2f} "
              f"{np.mean([r['th_kill_pct'] for r in sub]):9.2f} "
              f"{np.mean([r['cross_50_pct'] for r in sub]):7.2f} "
              f"{np.mean([r['dest_pct_when_not_3star'] for r in sub if r['dest_pct_when_not_3star'] is not None]):11.2f}")
    print(f"\nWrote {out}\nTotal wall time: {time.perf_counter() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()