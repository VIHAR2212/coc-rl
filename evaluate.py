from pathlib import Path
import numpy as np
from sim import CoCEnv
from agents.rule_based import rule_based_action

BASES_DIR = Path(__file__).resolve().parent / "data" / "bases"


def evaluate_base(base_file, episodes=20):
    env, res = CoCEnv(base_file=base_file), []
    for ep in range(episodes):
        env.reset(seed=ep)
        done, i, info = False, 0, {}
        while not done:
            _, _, term, trunc, info = env.step(rule_based_action(env, i))
            done, i = term or trunc, i + 1
        res.append((info["destruction"], info["stars"]))
    d, s = zip(*res)
    return float(np.mean(d)), float(np.mean(s))


def run_baseline(episodes=20):
    bases = sorted(BASES_DIR.glob("*.json"))
    print(f"{'Base':<14} {'Destruction':>12} {'Stars':>8}")
    print("-" * 36)
    for path in bases:
        mean_d, mean_s = evaluate_base(path.name, episodes=episodes)
        print(f"{path.name:<14} {mean_d * 100:>11.1f}% {mean_s:>8.2f}")


if __name__ == "__main__":
    run_baseline()
