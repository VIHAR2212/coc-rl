"""Baseline attacker: deploy all Giants first, then remaining troops in waves."""


def _pick_deploy_tile(env, preferred_x, target_y):
    """Return a valid deployable (x, y) near (preferred_x, target_y)."""
    for x in (preferred_x, 1, 0, 2, 3):
        if env._deployable(x, target_y):
            return x, target_y
    for dy in range(1, env.grid):
        for y in (target_y - dy, target_y + dy):
            for x in (preferred_x, 0, 1, 2):
                if env._deployable(x, y):
                    return x, y
    return 0, 0


def rule_based_action(env, step_idx):
    keys = env.troop_keys
    mid = env.grid // 2
    y_spread = mid + ((step_idx % 13) - 6)

    giant_keys = [k for k in keys if k.startswith("giant") and env.army_left.get(k, 0) > 0]
    if giant_keys:
        k = giant_keys[0]
        x, y = _pick_deploy_tile(env, 2, mid + ((step_idx % 5) - 2) * 2)
        return [keys.index(k) + 1, x, y]

    wb_keys = [k for k in keys if k.startswith("wall_breaker") and env.army_left.get(k, 0) > 0]
    if wb_keys:
        k = wb_keys[0]
        x, y = _pick_deploy_tile(env, 1, y_spread)
        return [keys.index(k) + 1, x, y]

    # Cycle through remaining troop types in waves so melee and ranged support each other.
    rest = [k for k in keys if env.army_left.get(k, 0) > 0]
    if rest:
        k = rest[step_idx % len(rest)]
        x, y = _pick_deploy_tile(env, 1, y_spread)
        return [keys.index(k) + 1, x, y]

    return [0, 0, 0]
