"""M10 Step 1e: Record expert demonstrations from left_wave across 100 train layouts.

Records:
- 100 train layouts (data/bases_gen/train/gen_base_000.json .. gen_base_099.json)
- All 7 TH8 armies
- Seeds >= 1000
- Maps continuous deployments to discrete edge sectors (16 sectors)
- Replays mapped actions to verify fidelity
- Saves to data/demos/m10_train_demos.npz (gitignored)
"""

import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.rule_based import rule_based_action
from sim import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv

DATA_DIR = ROOT / "data"
TRAIN_DIR = DATA_DIR / "bases_gen" / "train"
DEMOS_DIR = DATA_DIR / "demos"
DEMOS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_ARMIES = [
    "giant_barch",
    "barch",
    "goblin_giant",
    "mixed_wb",
    "mass_dragons",
    "gowiva",
    "hog_rush",
]


def map_deploy_to_sector(rx: float, ry: float, sector_tiles: list[list[tuple[int, int]]]) -> tuple[int, float]:
    """Map coordinate (rx, ry) to the sector whose tile set is closest in Euclidean distance."""
    best_sec = 0
    best_dist = float("inf")
    for s, tiles in enumerate(sector_tiles):
        if not tiles:
            continue
        d = min(math.hypot(rx - tx, ry - ty) for tx, ty in tiles)
        if d < best_dist:
            best_dist = d
            best_sec = s
    return best_sec, best_dist


def collect_m10_demos(
    n_layouts: int = 100,
    armies: list[str] = DEFAULT_ARMIES,
    start_seed: int = 1000,
    episodes_per_pair: int = 1,
) -> dict:
    layout_paths = sorted(TRAIN_DIR.glob("gen_base_*.json"))[:n_layouts]
    print("=" * 80)
    print("M10 STEP 1e: RECORDING DEMONSTRATIONS ACROSS 100 TRAIN LAYOUTS")
    print(f"Layouts: {len(layout_paths)} layouts ({layout_paths[0].name} .. {layout_paths[-1].name})")
    print(f"Armies: {len(armies)} armies ({armies})")
    print(f"Seeds: {start_seed} .. {start_seed + episodes_per_pair - 1} ({episodes_per_pair} ep per pair)")
    total_episodes = len(layout_paths) * len(armies) * episodes_per_pair
    print(f"Total episodes to record: {total_episodes:,}")
    print("=" * 80, flush=True)

    all_grids = []
    all_armies = []
    all_masks = []
    all_actions = []
    all_layout_ids = []
    all_army_ids = []

    mapping_distances = []
    total_deploys = 0
    masked_deploys = 0

    raw_dests, raw_stars = [], []
    replay_dests, replay_stars = [], []

    t0 = time.perf_counter()

    for l_idx, layout_p in enumerate(layout_paths):
        base_name = layout_p.name
        for a_idx, army_name in enumerate(armies):
            for ep_offset in range(episodes_per_pair):
                seed = start_seed + ep_offset

                # 1. Run raw left_wave and record decisions
                raw_env = CoCEnv(base_file=str(layout_p), army=army_name)
                wrap_env = ActionMaskCoCEnv(bases=[str(layout_p)], armies=[army_name], shaping_mode="stars_aware")

                raw_obs, _ = raw_env.reset(seed=seed)
                wrap_obs, _ = wrap_env.reset(seed=seed)

                ep_actions = []
                step_idx = 0
                done = False

                while not done:
                    obs_dict = wrap_obs
                    mask = wrap_env.action_masks()

                    # Query raw left_wave action
                    act = rule_based_action(raw_env, step_idx)
                    kind_raw, rx, ry = act

                    if kind_raw == 0:
                        mapped_action = 0  # Wait
                    else:
                        troop_kind = kind_raw - 1
                        sec, dist = map_deploy_to_sector(rx, ry, wrap_env._sector_tiles)
                        mapping_distances.append(dist)
                        mapped_action = 1 + troop_kind * wrap_env.num_sectors + sec

                        total_deploys += 1
                        if not mask[mapped_action]:
                            masked_deploys += 1
                            valid = np.where(mask)[0]
                            mapped_action = int(valid[0]) if len(valid) > 0 else 0

                    all_grids.append(obs_dict["grid"].astype(np.float32))
                    all_armies.append(obs_dict["army"].astype(np.float32))
                    all_masks.append(mask.astype(bool))
                    all_actions.append(int(mapped_action))
                    all_layout_ids.append(l_idx)
                    all_army_ids.append(a_idx)

                    ep_actions.append(mapped_action)

                    # Step both environments
                    raw_obs, _, r_term, r_trunc, r_info = raw_env.step(act)
                    wrap_obs, _, w_term, w_trunc, w_info = wrap_env.step(mapped_action)

                    done = r_term or r_trunc
                    step_idx += 1

                raw_dests.append(float(r_info.get("destruction", 0.0)) * 100.0)
                raw_stars.append(int(r_info.get("stars", 0)))
                replay_dests.append(float(w_info.get("destruction", 0.0)) * 100.0)
                replay_stars.append(int(w_info.get("stars", 0)))

        if (l_idx + 1) % 10 == 0 or (l_idx + 1) == len(layout_paths):
            elapsed = time.perf_counter() - t0
            eps_done = (l_idx + 1) * len(armies) * episodes_per_pair
            mean_dist = float(np.mean(mapping_distances)) if mapping_distances else 0.0
            print(f"  Processed {l_idx + 1:3d}/{len(layout_paths)} layouts ({eps_done:4d} eps) in {elapsed:.1f}s | Mean mapping dist: {mean_dist:.2f} tiles", flush=True)

    dur = time.perf_counter() - t0
    print(f"\nDemonstration recording finished in {dur:.1f}s.")

    # Convert to numpy arrays
    grids_arr = np.array(all_grids, dtype=np.float32)
    armies_arr = np.array(all_armies, dtype=np.float32)
    masks_arr = np.array(all_masks, dtype=bool)
    actions_arr = np.array(all_actions, dtype=np.int32)
    layouts_arr = np.array(all_layout_ids, dtype=np.int32)
    army_ids_arr = np.array(all_army_ids, dtype=np.int32)

    out_file = DEMOS_DIR / "m10_train_demos.npz"
    np.savez_compressed(
        out_file,
        grids=grids_arr,
        armies=armies_arr,
        masks=masks_arr,
        actions=actions_arr,
        layout_ids=layouts_arr,
        army_ids=army_ids_arr,
    )

    size_mb = out_file.stat().st_size / (1024 * 1024)
    print(f"Saved dataset to {out_file.name} ({size_mb:.2f} MB, {len(actions_arr):,} total steps).")

    mean_raw_d = float(np.mean(raw_dests))
    mean_rep_d = float(np.mean(replay_dests))
    gap_d = mean_rep_d - mean_raw_d
    mean_map_dist = float(np.mean(mapping_distances))
    max_map_dist = float(np.max(mapping_distances))
    masked_pct = (masked_deploys / max(1, total_deploys)) * 100.0

    print("\nMapping & Replay Verification Summary:")
    print(f"  Total Deployments:   {total_deploys:,}")
    print(f"  Mean Mapping Error:  {mean_map_dist:.2f} tiles (max: {max_map_dist:.2f})")
    print(f"  Mask Violations:     {masked_deploys} ({masked_pct:.3f}%)")
    print(f"  Raw Dest (Mean):     {mean_raw_d:.2f}%")
    print(f"  Replay Dest (Mean):  {mean_rep_d:.2f}%")
    print(f"  Replay Gap:          {gap_d:+.2f} pp")

    return {
        "total_steps": len(actions_arr),
        "total_deploys": total_deploys,
        "mean_mapping_dist": mean_map_dist,
        "raw_dest": mean_raw_d,
        "replay_dest": mean_rep_d,
        "replay_gap": gap_d,
    }


if __name__ == "__main__":
    collect_m10_demos()
