import os
import subprocess
import sys

import numpy as np

from sim import CoCEnv


def test_render_rgb_array():
    env = CoCEnv(base_file="base03.json", render_mode="rgb_array")
    env.reset(seed=0)
    env.step([1, 2, 20])
    frame = env.render()
    assert isinstance(frame, np.ndarray)
    assert frame.ndim == 3 and frame.shape[2] == 3
    assert frame.dtype == np.uint8
    assert frame.max() > 0
    env.close()


def test_play_human_smoke():
    env_vars = os.environ.copy()
    env_vars["SDL_VIDEODRIVER"] = "dummy"
    proc = subprocess.run(
        [sys.executable, "play_human.py", "--smoke-test"],
        env=env_vars,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

