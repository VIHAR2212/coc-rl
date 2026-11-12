"""Smart-funnel baseline: attack the side nearest the Town Hall/defenses in a wide line."""
from agents.helpers import edge_ring_tiles, next_available_troop


def _choose_front_tiles(env) -> list[tuple[int, int]]:
    ring = edge_ring_tiles(env)
    if not ring:
        return []
    th = next((b for b in env._non_walls if b.is_town_hall and b.hp > 0), None)
    if th is None:
        return ring[: min(16, len(ring))]

    # Score deployable ring tiles by proximity to Town Hall (and nearest defense), then take the best front.
    scored = sorted(
        ring,
        key=lambda pt: (pt[0] + 0.5 - th.cx) ** 2 + (pt[1] + 0.5 - th.cy) ** 2,
    )
    front = scored[: min(18, len(scored))]
    # Sort front along its dominant axis so sequential deploys sweep side-to-side instead of clumping.
    xs = [p[0] for p in front]
    ys = [p[1] for p in front]
    if max(xs) - min(xs) >= max(ys) - min(ys):
        front.sort(key=lambda pt: pt[0])
    else:
        front.sort(key=lambda pt: pt[1])
    return front


def smart_funnel_action(env, step_idx: int) -> list[int]:
    key = next_available_troop(env, ["giant", "wall_breaker"], step_idx, cycle_rest=True)
    if key is None:
        return [0, 0, 0]

    front = _choose_front_tiles(env)
    if not front:
        return [0, 0, 0]

    m = len(front)
    if key.startswith("wall_breaker"):
        # Wall Breakers go into the middle of the front behind tanking Giants.
        center = m // 2
        idx = max(0, min(m - 1, center + int(env.np_random.integers(-1, 2))))
    elif key.startswith("giant"):
        # Spread Giants cleanly along the middle 70% of the front.
        lo = m // 6
        hi = max(lo + 1, m - lo)
        span = hi - lo
        idx = lo + ((step_idx * 3 + int(env.np_random.integers(0, 2))) % span)
    else:
        # Spread melee and ranged troops across the whole funnel front to minimize splash loss.
        idx = (step_idx * 5 + int(env.np_random.integers(-1, 2))) % m

    x, y = front[idx]
    return [env.troop_keys.index(key) + 1, x, y]

