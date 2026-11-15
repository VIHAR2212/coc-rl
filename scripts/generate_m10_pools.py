"""Generate train and held-out layout pools for Milestone M10.

Generates:
1. data/bases_gen/train/: 300 procedural layouts (seeds 0..299).
2. data/bases_gen/heldout_v2/: 30 fresh held-out layouts (seeds >= 10000).
   Enforces a strict minimum layout distance threshold against all training layouts
   and legacy bases (base02..base10).
3. Manifests with layout metadata, styles, seed lists, and SHA256 hashes.
"""

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.base_generator import generate_base, STYLES, BUILDING_SIZES
from scripts.validate_base import validate_base, _load_defs, _load_th8_limits

DATA_DIR = ROOT / "data"
BASES_GEN_DIR = DATA_DIR / "bases_gen"
TRAIN_DIR = BASES_GEN_DIR / "train"
HELDOUT_DIR = BASES_GEN_DIR / "heldout_v2"
LEGACY_DIR = DATA_DIR / "bases"

GRID_SIZE = 44
MAX_EUCLIDEAN = math.sqrt(2 * (GRID_SIZE ** 2))  # ~62.22 tiles
MIN_DISTANCE_THRESHOLD = 0.160  # Documented threshold for heldout rejection (ensures substantial divergence)


def get_occupancy_grid(base: dict[str, Any]) -> np.ndarray:
    """Create a 44x44 binary mask of occupied tiles."""
    grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=bool)
    for b in base["buildings"]:
        b_type = b["type"]
        size = BUILDING_SIZES.get(b_type, 3)
        x, y = b["x"], b["y"]
        grid[y:y + size, x:x + size] = True
    return grid


def get_building_centers(base: dict[str, Any]) -> dict[str, list[tuple[float, float]]]:
    """Get list of (cx, cy) coordinates grouped by building type."""
    centers: dict[str, list[tuple[float, float]]] = {}
    for b in base["buildings"]:
        b_type = b["type"]
        size = BUILDING_SIZES.get(b_type, 3)
        cx = b["x"] + size / 2.0
        cy = b["y"] + size / 2.0
        centers.setdefault(b_type, []).append((cx, cy))
    return centers


def compute_layout_distance(base_a: dict[str, Any], base_b: dict[str, Any]) -> float:
    """Compute normalized layout distance D(A, B) in [0, 1].

    Combines:
    1. Jaccard distance over tile occupancy grid: d_occ = 1 - (A n B) / (A u B)
    2. Directed Chamfer distance over non-wall building center coordinates.
    """
    occ_a = get_occupancy_grid(base_a)
    occ_b = get_occupancy_grid(base_b)

    intersection = np.logical_and(occ_a, occ_b).sum()
    union = np.logical_or(occ_a, occ_b).sum()
    d_occ = 1.0 - (intersection / union) if union > 0 else 0.0

    centers_a = get_building_centers(base_a)
    centers_b = get_building_centers(base_b)

    # Per-type chamfer distance (excluding wall for efficiency; wall is captured in occupancy)
    type_distances = []
    all_types = set(centers_a.keys()).union(centers_b.keys()) - {"wall"}
    for t in all_types:
        pts_a = centers_a.get(t, [])
        pts_b = centers_b.get(t, [])
        if not pts_a or not pts_b:
            type_distances.append(1.0)
            continue

        # Chamfer distance between pts_a and pts_b
        d_ab = []
        for ax, ay in pts_a:
            min_d = min(math.hypot(ax - bx, ay - by) for bx, by in pts_b)
            d_ab.append(min_d)
        d_ba = []
        for bx, by in pts_b:
            min_d = min(math.hypot(bx - ax, by - ay) for ax, ay in pts_a)
            d_ba.append(min_d)

        mean_chamfer = (sum(d_ab) / len(d_ab) + sum(d_ba) / len(d_ba)) / 2.0
        norm_chamfer = min(1.0, mean_chamfer / (MAX_EUCLIDEAN * 0.5))
        type_distances.append(norm_chamfer)

    d_buildings = float(np.mean(type_distances)) if type_distances else 0.0
    combined = 0.5 * d_occ + 0.5 * d_buildings
    return float(combined)


def compute_sha256(data_dict: dict[str, Any]) -> str:
    serialized = json.dumps(data_dict, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def main():
    TRAIN_DIR.mkdir(parents=True, exist_ok=True)
    HELDOUT_DIR.mkdir(parents=True, exist_ok=True)

    defs = _load_defs()
    limits = _load_th8_limits()

    # Load legacy bases (base02..base10)
    legacy_bases: dict[str, dict[str, Any]] = {}
    for i in range(2, 11):
        p = LEGACY_DIR / f"base{i:02d}.json"
        if p.exists():
            legacy_bases[p.name] = json.loads(p.read_text(encoding="utf-8"))

    print(f"Loaded {len(legacy_bases)} legacy bases for divergence checking.")

    # 1. Generate 300 Train Layouts (seeds 0..299)
    print("\n--- Generating 300 Training Layouts (seeds 0..299) ---")
    train_manifest: list[dict[str, Any]] = []
    train_bases: list[dict[str, Any]] = []

    for seed in range(300):
        style = STYLES[seed % len(STYLES)]
        base = generate_base(seed=seed, style=style)
        filename = f"gen_base_{seed:03d}.json"
        out_path = TRAIN_DIR / filename
        out_path.write_text(json.dumps(base, indent=2), encoding="utf-8")

        # Validate
        errs = validate_base(out_path, defs=defs, limits=limits)
        if errs:
            print(f"ERROR: Training base {filename} failed validation: {errs}")
            sys.exit(1)

        counts = {}
        for b in base["buildings"]:
            counts[b["type"]] = counts.get(b["type"], 0) + 1

        entry = {
            "name": filename,
            "seed": seed,
            "style": style,
            "buildings_count": len(base["buildings"]),
            "walls_count": counts.get("wall", 0),
            "defenses_count": len(base["buildings"]) - counts.get("wall", 0),
            "sha256": compute_sha256(base),
        }
        train_manifest.append(entry)
        train_bases.append(base)

    print(f"Successfully generated and validated {len(train_bases)} training layouts.")

    # 2. Compute Train Pool Diversity Metrics (sample pairwise distances)
    print("\n--- Computing Diversity Statistics on Training Pool ---")
    rng = np.random.default_rng(42)
    sample_pairs = [rng.choice(300, size=2, replace=False) for _ in range(500)]
    train_distances = [compute_layout_distance(train_bases[i], train_bases[j]) for i, j in sample_pairs]

    mean_d = float(np.mean(train_distances))
    std_d = float(np.std(train_distances))
    min_d = float(np.min(train_distances))
    p10_d = float(np.percentile(train_distances, 10))
    p50_d = float(np.median(train_distances))
    max_d = float(np.max(train_distances))

    print(f"Train Pairwise Distances (500 samples):")
    print(f"  Mean:   {mean_d:.4f} +/- {std_d:.4f}")
    print(f"  Min:    {min_d:.4f}")
    print(f"  P10:    {p10_d:.4f}")
    print(f"  Median: {p50_d:.4f}")
    print(f"  Max:    {max_d:.4f}")

    # 3. Generate 30 Fresh Held-Out Layouts (seeds >= 10000)
    print(f"\n--- Generating 30 Fresh Held-Out Layouts (Threshold >= {MIN_DISTANCE_THRESHOLD}) ---")
    heldout_manifest: list[dict[str, Any]] = []
    heldout_bases: list[dict[str, Any]] = []

    seed_candidate = 10000
    rejected_count = 0

    while len(heldout_bases) < 30:
        idx = len(heldout_bases)
        style = STYLES[seed_candidate % len(STYLES)]
        candidate = generate_base(seed=seed_candidate, style=style)

        # Compute minimum distance to all 300 train layouts
        min_to_train = min(compute_layout_distance(candidate, tb) for tb in train_bases)
        # Compute minimum distance to legacy layouts
        min_to_legacy = min(compute_layout_distance(candidate, lb) for lb in legacy_bases.values())

        if min_to_train < MIN_DISTANCE_THRESHOLD or min_to_legacy < MIN_DISTANCE_THRESHOLD:
            rejected_count += 1
            print(f"  [REJECT] Seed {seed_candidate} (style={style}): min_train={min_to_train:.3f}, min_legacy={min_to_legacy:.3f}")
            seed_candidate += 1
            continue

        filename = f"heldout_base_{idx:02d}.json"
        out_path = HELDOUT_DIR / filename
        out_path.write_text(json.dumps(candidate, indent=2), encoding="utf-8")

        errs = validate_base(out_path, defs=defs, limits=limits)
        if errs:
            print(f"ERROR: Held-out base {filename} failed validation: {errs}")
            sys.exit(1)

        counts = {}
        for b in candidate["buildings"]:
            counts[b["type"]] = counts.get(b["type"], 0) + 1

        entry = {
            "name": filename,
            "seed": seed_candidate,
            "style": style,
            "buildings_count": len(candidate["buildings"]),
            "walls_count": counts.get("wall", 0),
            "min_dist_to_train": round(min_to_train, 4),
            "min_dist_to_legacy": round(min_to_legacy, 4),
            "sha256": compute_sha256(candidate),
        }
        heldout_manifest.append(entry)
        heldout_bases.append(candidate)
        print(f"  [ACCEPT #{idx:02d}] Seed {seed_candidate:5d} ({style:16s}): min_train={min_to_train:.3f}, min_legacy={min_to_legacy:.3f}")
        seed_candidate += 1

    print(f"\nGenerated 30 held-out bases (Rejected {rejected_count} candidate layouts below threshold).")

    # 4. Save Manifests
    train_manifest_path = BASES_GEN_DIR / "manifest_train.json"
    heldout_manifest_path = BASES_GEN_DIR / "manifest_heldout_v2.json"

    train_manifest_path.write_text(json.dumps({
        "pool": "train",
        "count": len(train_manifest),
        "styles_distribution": {s: sum(1 for e in train_manifest if e["style"] == s) for s in STYLES},
        "distance_stats_sample": {
            "mean": mean_d,
            "std": std_d,
            "min": min_d,
            "p10": p10_d,
            "median": p50_d,
            "max": max_d,
        },
        "layouts": train_manifest,
    }, indent=2), encoding="utf-8")

    heldout_manifest_path.write_text(json.dumps({
        "pool": "heldout_v2",
        "count": len(heldout_manifest),
        "min_distance_threshold": MIN_DISTANCE_THRESHOLD,
        "rejected_candidates": rejected_count,
        "styles_distribution": {s: sum(1 for e in heldout_manifest if e["style"] == s) for s in STYLES},
        "layouts": heldout_manifest,
    }, indent=2), encoding="utf-8")

    print(f"Saved manifests to {train_manifest_path.name} and {heldout_manifest_path.name}.")


if __name__ == "__main__":
    main()
