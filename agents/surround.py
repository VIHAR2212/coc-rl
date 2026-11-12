"""Surround baseline: deploy Giants and support evenly around all four sides of the base."""
from agents.helpers import edge_ring_tiles, next_available_troop


def surround_action(env, step_idx: int) -> list[int]:
    key = next_available_troop(env, ["giant", "wall_breaker"], step_idx, cycle_rest=True)
    if key is None:
        return [0, 0, 0]

    ring = edge_ring_tiles(env)
    if not ring:
        return [0, 0, 0]

    n = len(ring)
    # Step around the ring in wide jumps (golden-ratio-like stride) + seeded jitter so
    # multiple units avoid clustering on a single splash tile.
    stride = max(1, int(n * 0.381966))
    jitter = int(env.np_random.integers(-2, 3))
    idx = (step_idx * stride + jitter) % n
    x, y = ring[idx]
    return [env.troop_keys.index(key) + 1, x, y]

