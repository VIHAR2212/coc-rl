from sim import CoCEnv


def test_random_episode_runs():
    env = CoCEnv()
    env.reset(seed=0)
    info = {}
    for _ in range(200):
        _, _, term, trunc, info = env.step(env.action_space.sample())
        if term or trunc:
            break
    assert 0 <= info["destruction"] <= 1
