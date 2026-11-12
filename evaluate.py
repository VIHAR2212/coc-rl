import numpy as np
from sim import CoCEnv
from agents.rule_based import rule_based_action


def run_baseline(episodes=20):
    env, res = CoCEnv(), []
    for ep in range(episodes):
        env.reset(seed=ep)
        done, i, info = False, 0, {}
        while not done:
            _, _, term, trunc, info = env.step(rule_based_action(env, i))
            done, i = term or trunc, i + 1
        res.append((info["destruction"], info["stars"]))
    d, s = zip(*res)
    print(f"rule-based: destruction {np.mean(d)*100:.1f}%  stars {np.mean(s):.2f}")


if __name__ == "__main__":
    run_baseline()
