"""Baseline attacker: Giants first on the left edge, then Barbarians and Archers behind them."""


def rule_based_action(env, step_idx):
    keys, y = env.troop_keys, env.grid // 2
    if step_idx < 2 and env.army_left.get("giant_l8", 0) > 0:
        return [keys.index("giant_l8") + 1, 2, y + step_idx * 2 - 1]
    if step_idx >= 4:
        for k in ("barbarian_l8", "archer_l8"):
            if env.army_left.get(k, 0) > 0:
                return [keys.index(k) + 1, 1, y + (step_idx % 5) - 2]
    return [0, 0, 0]
