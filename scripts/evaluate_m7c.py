"""M7c: held-out evaluation on all 28 pairs (base07..base10 x all 7 TH8 armies).

Agents compared per (base, army) pair, 100 seeded episodes each:
  3 rule-based baselines, random_masked, the 3 Part B seeds, the 3 M7c no-anti-collapse
  ablation seeds, plus the 3-seed aggregates of Part B and the ablation.

Outputs:
  results/m7c_all_armies.csv   per-pair rows for every agent
  results/m7c_summary.csv      agent-level means, bootstrap 95% CIs, paired deltas vs left_wave
  results/evaluate_m7c.log     full console log

Verification/evaluation only - no training and no stat changes.
"""
import csv
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_m7b_partB import (  # noqa: E402
    EPISODES_PER_PAIR,
    _eval_baseline_pair,
    _eval_ppo_seed_pair,
    _eval_random_masked_pair,
    bootstrap_ci,
)

HELD_OUT_BASES = ["base07.json", "base08.json", "base09.json", "base10.json"]
PART_B_MODELS = [f"models/ppo_m7b_seed{s}.zip" for s in (42, 43, 44)]
ABLATION_MODELS = [f"models/ppo_m7c_noac_seed{s}.zip" for s in (42, 43, 44)]
RESULTS = ROOT / "results"
FIELDS = ["agent", "base", "army", "episodes", "mean_dest_pct", "std_dest_pct",
          "min_dest_pct", "max_dest_pct", "unique_dest_outcomes", "mean_stars", "three_star_pct"]


def _armies() -> list[str]:
    raw = json.loads((ROOT / "data" / "armies.json").read_text(encoding="utf-8"))
    return [k for k in raw if not k.startswith("_")]


class Tee:
    def __init__(self, path: Path):
        self.fh = path.open("w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, text):
        self.stdout.write(text)
        self.fh.write(text)

    def flush(self):
        self.stdout.flush()
        self.fh.flush()

    def close(self):
        self.fh.close()


def _label_for(model_path: str) -> str:
    stem = Path(model_path).stem  # ppo_m7b_seed42 / ppo_m7c_noac_seed42
    if stem.startswith("ppo_m7b_seed"):
        return f"maskable_ppo_partB_seed{stem.split('seed')[1]}"
    if stem.startswith("ppo_m7c_noac_seed"):
        return f"maskable_ppo_noac_seed{stem.split('seed')[1]}"
    return stem


def _condense(rows: list[dict], label: str) -> list[dict]:
    """Concatenate raw episode lists of several seeds into one 300-episode row set."""
    dests = [d for r in rows for d in r["raw_dests"]]          # fractions 0..1
    stars = [s for r in rows for s in r["raw_stars"]]
    three = [t for r in rows for t in r["raw_3stars"]]
    return [{
        "agent": label,
        "base": rows[0]["base"],
        "army": rows[0]["army"],
        "episodes": len(dests),
        "mean_dest_pct": round(float(np.mean(dests)) * 100.0, 4),
        "std_dest_pct": round(float(np.std(dests)) * 100.0, 4),
        "min_dest_pct": round(float(np.min(dests)) * 100.0, 4),
        "max_dest_pct": round(float(np.max(dests)) * 100.0, 4),
        "unique_dest_outcomes": len(set(round(d, 4) for d in dests)),
        "mean_stars": round(float(np.mean(stars)), 4),
        "three_star_pct": round(float(np.mean(three)) * 100.0, 4),
    }]


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({k: r[k] for k in FIELDS} for r in rows)


def main(workers: int = 2) -> None:
    t0 = time.perf_counter()
    armies = _armies()
    pairs = [(b, a) for b in HELD_OUT_BASES for a in armies]
    print("=== M7c: ALL-ARMY HELD-OUT EVALUATION ===", flush=True)
    print(f"Bases: {HELD_OUT_BASES}", flush=True)
    print(f"Armies ({len(armies)}): {armies}", flush=True)
    print(f"Pairs: {len(pairs)} | episodes/pair: {EPISODES_PER_PAIR} | workers: {workers}", flush=True)
    print(f"Part B models: {PART_B_MODELS}", flush=True)
    print(f"Ablation models: {ABLATION_MODELS}", flush=True)

    # --- 1. baselines ---
    baseline_tasks = [(s, b, a, EPISODES_PER_PAIR)
                      for s in ("left_wave", "surround", "smart_funnel") for b, a in pairs]
    print(f"\n--- Baselines ({len(baseline_tasks)} tasks) ---", flush=True)
    baseline_rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_baseline_pair, baseline_tasks), 1):
            baseline_rows.append(res)
            if idx % 14 == 0 or idx == len(baseline_tasks):
                print(f"[{idx}/{len(baseline_tasks)}] {res['agent']} / {res['base']} / {res['army']} "
                      f"({time.perf_counter() - t0:.1f}s)", flush=True)

    # --- 2. random_masked ---
    random_tasks = [(b, a, EPISODES_PER_PAIR) for b, a in pairs]
    print(f"\n--- random_masked ({len(random_tasks)} tasks) ---", flush=True)
    random_rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_random_masked_pair, random_tasks), 1):
            random_rows.append(res)
            if idx % 14 == 0 or idx == len(random_tasks):
                print(f"[{idx}/{len(random_tasks)}] random_masked / {res['base']} / {res['army']} "
                      f"({time.perf_counter() - t0:.1f}s)", flush=True)

    # --- 3. PPO seeds (Part B + ablation) ---
    model_paths = PART_B_MODELS + ABLATION_MODELS
    ppo_tasks = [(m, b, a, EPISODES_PER_PAIR) for m in model_paths for b, a in pairs]
    print(f"\n--- PPO models ({len(ppo_tasks)} tasks) ---", flush=True)
    ppo_raw = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for idx, res in enumerate(pool.map(_eval_ppo_seed_pair, ppo_tasks), 1):
            res["agent"] = _label_for(res["diag"]["model_file"])
            ppo_raw.append(res)
            if idx % 14 == 0 or idx == len(ppo_tasks):
                print(f"[{idx}/{len(ppo_tasks)}] {res['agent']} / {res['base']} / {res['army']} "
                      f"({time.perf_counter() - t0:.1f}s)", flush=True)

    # --- 4. 3-seed aggregates per pair ---
    agg_rows = []
    for group, label in (
        (PART_B_MODELS, "maskable_ppo_partB_3seed"),
        (ABLATION_MODELS, "maskable_ppo_noac_3seed"),
    ):
        for b, a in pairs:
            names = {Path(m).name for m in group}
            seed_rows = [r for r in ppo_raw if r["diag"]["model_file"] in names and r["base"] == b and r["army"] == a]
            agg_rows.extend(_condense(seed_rows, label))

    all_rows = baseline_rows + random_rows + ppo_raw + agg_rows
    _write(RESULTS / "m7c_all_armies.csv", all_rows)

    # --- 5. Action diagnostics per (model, pair) ---
    diags = [dict(r["diag"]) for r in ppo_raw]
    with (RESULTS / "m7c_action_diagnostics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(diags[0].keys()))
        writer.writeheader()
        writer.writerows(diags)

    # --- 5. Summary with bootstrap CIs + paired deltas vs left_wave ---
    order = ["left_wave", "smart_funnel", "surround", "random_masked",
             "maskable_ppo_partB_seed42", "maskable_ppo_partB_seed43", "maskable_ppo_partB_seed44",
             "maskable_ppo_partB_3seed",
             "maskable_ppo_noac_seed42", "maskable_ppo_noac_seed43", "maskable_ppo_noac_seed44",
             "maskable_ppo_noac_3seed"]
    by_agent = {name: [r for r in all_rows if r["agent"] == name] for name in order}
    lw = {(r["base"], r["army"]): r for r in by_agent["left_wave"]}

    print("\n" + "=" * 118)
    print("M7c SUMMARY - 28 HELD-OUT PAIRS (base07..10 x 7 armies), per-pair bootstrap 95% CIs")
    print("=" * 118)
    header = (f"{'Agent':<30} {'Dest % [95% CI]':<24} {'Stars [95% CI]':<22} {'3-Star % [95% CI]':<20} "
              f"{'dDest vs left_wave':<22} {'dStars':<18}")
    print(header)
    print("-" * 118)

    summary_rows = []
    for name in order:
        rows = by_agent[name]
        assert len(rows) == len(pairs), f"{name}: {len(rows)} rows"
        d = [r["mean_dest_pct"] for r in rows]
        s = [r["mean_stars"] for r in rows]
        t = [r["three_star_pct"] for r in rows]
        dm, dlo, dhi = bootstrap_ci(d)
        sm, slo, shi = bootstrap_ci(s)
        tm, tlo, thi = bootstrap_ci(t)
        if name == "left_wave":
            ddm = ddlo = ddhi = dsm = dslo = dshi = 0.0
        else:
            pair_dest = [r["mean_dest_pct"] - lw[(r["base"], r["army"])]["mean_dest_pct"] for r in rows]
            pair_stars = [r["mean_stars"] - lw[(r["base"], r["army"])]["mean_stars"] for r in rows]
            ddm, ddlo, ddhi = bootstrap_ci(pair_dest)
            dsm, dslo, dshi = bootstrap_ci(pair_stars)
        print(f"{name:<30} {dm:5.2f} [{dlo:5.2f}, {dhi:5.2f}]      {sm:4.2f} [{slo:4.2f}, {shi:4.2f}]    "
              f"{tm:5.2f} [{tlo:5.2f}, {thi:5.2f}]   {ddm:+5.2f} [{ddlo:+5.2f}, {ddhi:+5.2f}]  "
              f"{dsm:+5.3f} [{dslo:+5.3f}, {dshi:+5.3f}]")
        summary_rows.append({
            "agent": name,
            "pairs": len(rows),
            "episodes_per_pair": rows[0]["episodes"],
            "mean_dest_pct": round(dm, 4), "dest_ci_lo": round(dlo, 4), "dest_ci_hi": round(dhi, 4),
            "mean_stars": round(sm, 4), "stars_ci_lo": round(slo, 4), "stars_ci_hi": round(shi, 4),
            "three_star_pct": round(tm, 4), "three_star_ci_lo": round(tlo, 4), "three_star_ci_hi": round(thi, 4),
            "paired_dest_delta_vs_left_wave": round(ddm, 4),
            "paired_dest_ci_lo": round(ddlo, 4), "paired_dest_ci_hi": round(ddhi, 4),
            "paired_stars_delta_vs_left_wave": round(dsm, 4),
            "paired_stars_ci_lo": round(dslo, 4), "paired_stars_ci_hi": round(dshi, 4),
        })

    with (RESULTS / "m7c_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    # --- 6. Same-pair comparison restricted to the 16 Part A ground-army pairs ---
    ground_armies = ["giant_barch", "barch", "goblin_giant", "mixed_wb"]
    subset = [(b, a) for b, a in pairs if a in ground_armies]
    print("\n" + "=" * 118)
    print("SAME-SIMULATOR COMPARISON ON THE 16 PART-A GROUND-ARMY PAIRS (Part A itself is NOT comparable - see report)")
    print("=" * 118)
    for name in ["left_wave", "maskable_ppo_partB_3seed", "maskable_ppo_noac_3seed"]:
        rows = [r for r in by_agent[name] if (r["base"], r["army"]) in subset]
        d = [r["mean_dest_pct"] for r in rows]
        s = [r["mean_stars"] for r in rows]
        t = [r["three_star_pct"] for r in rows]
        dm, dlo, dhi = bootstrap_ci(d)
        sm, slo, shi = bootstrap_ci(s)
        tm, tlo, thi = bootstrap_ci(t)
        print(f"{name:<30} dest {dm:5.2f} [{dlo:5.2f}, {dhi:5.2f}]  stars {sm:4.2f} [{slo:4.2f}, {shi:4.2f}]  "
              f"3-star {tm:5.2f} [{tlo:5.2f}, {thi:5.2f}]")

    print(f"\nWrote {RESULTS / 'm7c_all_armies.csv'} ({len(all_rows)} rows), "
          f"{RESULTS / 'm7c_summary.csv'} and {RESULTS / 'm7c_action_diagnostics.csv'}")
    print(f"Total wall time: {time.perf_counter() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    tee = Tee(RESULTS / "evaluate_m7c.log")
    sys.stdout = tee
    try:
        main()
    finally:
        tee.flush()
        sys.stdout = tee.stdout
        tee.close()