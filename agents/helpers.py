"""Shared deploy-tile helpers for rule-based baseline strategies."""
import math
import numpy as np


def edge_ring_tiles(env) -> list[tuple[int, int]]:
    """Return deployable tiles adjacent to the forbidden base boundary, sorted around map center."""
    cache_key = id(env._deploy_mask)
    cached = getattr(env, "_cached_edge_ring", None)
    if cached is not None and cached[0] == cache_key:
        return cached[1]

    mask = env._deploy_mask > 0.5
    ys, xs = np.where(mask)
    h, w = mask.shape
    ring: list[tuple[int, int]] = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        # Prefer tiles right outside the deploy_margin border (closest valid tiles to buildings).
        adj_blocked = (
            (x > 0 and not mask[y, x - 1])
            or (x + 1 < w and not mask[y, x + 1])
            or (y > 0 and not mask[y - 1, x])
            or (y + 1 < h and not mask[y + 1, x])
        )
        if adj_blocked:
            ring.append((int(x), int(y)))

    if not ring:
        ring = [(int(x), int(y)) for y, x in zip(ys.tolist(), xs.tolist())]

    mid = env.grid / 2.0
    ring.sort(key=lambda pt: math.atan2(pt[1] - mid, pt[0] - mid))
    env._cached_edge_ring = (cache_key, ring)
    return ring


def next_available_troop(env, priorities: list[str], step_idx: int, cycle_rest: bool = True) -> str | None:
    """Return the next troop key with count > 0, prioritizing prefixes in order."""
    keys = env.troop_keys
    for prefix in priorities:
        matches = [k for k in keys if k.startswith(prefix) and env.army_left.get(k, 0) > 0]
        if matches:
            return matches[0]
    rest = [k for k in keys if env.army_left.get(k, 0) > 0]
    if not rest:
        return None
    return rest[step_idx % len(rest)] if cycle_rest else rest[0]

