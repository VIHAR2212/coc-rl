"""Baseline attacker: Giants first on the left edge, then Barbarians and Archers behind them."""


def _find_key(keys, prefix):
    return next((k for k in keys if k.startswith(prefix)), None)


def rule_based_action(env, step_idx):
    keys, y = env.troop_keys, env.grid // 2
    giant_key = _find_key(keys, "giant")
    if step_idx < 2 and giant_key and env.army_left.get(giant_key, 0) > 0:
        return [keys.index(giant_key) + 1, 2, y + step_idx * 2 - 1]
    if step_idx >= 4:
        for prefix in ("barbarian", "archer"):
            k = _find_key(keys, prefix)
            if k and env.army_left.get(k, 0) > 0:
                return [keys.index(k) + 1, 1, y + (step_idx % 5) - 2]
    return [0, 0, 0]
