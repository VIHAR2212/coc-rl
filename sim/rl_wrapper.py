"""Gymnasium wrapper adding valid-edge sector actions and action masks for MaskablePPO."""
import math
from typing import Any

import gymnasium as gym
import numpy as np
import torch as th
import torch.nn as nn
from gymnasium import spaces
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

from agents.helpers import edge_ring_tiles
from sim.env import CoCEnv

NUM_SECTORS = 16
TRAIN_BASES = ["base01.json", "base02.json", "base03.json", "base04.json"]
HELD_OUT_BASES = ["base05.json", "base06.json"]


class ActionMaskCoCEnv(gym.Env):
    """Wraps CoCEnv with discrete (troop, edge-sector) actions and exact validity masks."""

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        bases: list[str] | str = "base03.json",
        armies: list[str] | str | None = None,
        num_sectors: int = NUM_SECTORS,
        shaping_mode: str = "baseline",
        render_mode: str | None = None,
    ):
        super().__init__()
        self.base_pool = [bases] if isinstance(bases, str) else list(bases)
        if armies is None:
            self.army_pool = ["giant_barch", "barch", "goblin_giant", "mixed_wb"]
        elif isinstance(armies, str):
            self.army_pool = [armies]
        else:
            self.army_pool = list(armies)
        self.num_sectors = num_sectors
        self.shaping_mode = shaping_mode
        self.render_mode = render_mode

        self.env = CoCEnv(base_file=self.base_pool[0], army=self.army_pool[0], render_mode=render_mode)
        self.troop_keys = list(self.env.troop_keys)
        self.n_troops = len(self.troop_keys)
        # 0 = wait; 1..n_troops*num_sectors = deploy troop k in sector s
        self.action_space = spaces.Discrete(1 + self.n_troops * self.num_sectors)
        self.observation_space = self.env.observation_space

        self._sector_tiles: list[list[tuple[int, int]]] = [[] for _ in range(self.num_sectors)]
        self._sector_cursor: list[int] = [0] * self.num_sectors
        self._ep_idx = 0

    def _rebuild_sectors(self) -> None:
        ring = edge_ring_tiles(self.env)
        buckets: list[list[tuple[int, int]]] = [[] for _ in range(self.num_sectors)]
        mid = self.env.grid / 2.0
        for x, y in ring:
            ang = math.atan2(y - mid, x - mid)  # [-pi, pi]
            frac = (ang + math.pi) / (2.0 * math.pi)
            sec = min(self.num_sectors - 1, max(0, int(frac * self.num_sectors)))
            buckets[sec].append((x, y))
        self._sector_tiles = buckets
        self._sector_cursor = [0] * self.num_sectors

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        if seed is not None:
            base_idx = int(self.np_random.integers(0, len(self.base_pool)))
            army_idx = int(self.np_random.integers(0, len(self.army_pool)))
        else:
            base_idx = (self._ep_idx // len(self.army_pool)) % len(self.base_pool)
            army_idx = self._ep_idx % len(self.army_pool)
        self._ep_idx += 1

        chosen_base = (options or {}).get("base_file", self.base_pool[base_idx])
        chosen_army = (options or {}).get("army", self.army_pool[army_idx])
        self.env = CoCEnv(base_file=chosen_base, army=chosen_army, render_mode=self.render_mode)
        obs, info = self.env.reset(seed=seed)
        self._rebuild_sectors()
        info = dict(info)
        info.update({"base": chosen_base, "army": chosen_army})
        return obs, info

    def action_masks(self) -> np.ndarray:
        mask = np.zeros(1 + self.n_troops * self.num_sectors, dtype=bool)
        has_army = any(self.env.army_left[k] > 0 for k in self.troop_keys)
        # Allow Wait after at least one troop is placed, or once all troops are deployed.
        mask[0] = (not has_army) or (len(self.env.troops) > 0)
        if has_army:
            for k_idx, k in enumerate(self.troop_keys):
                if self.env.army_left[k] <= 0:
                    continue
                base_a = 1 + k_idx * self.num_sectors
                for s in range(self.num_sectors):
                    if self._sector_tiles[s]:
                        mask[base_a + s] = True
        return mask

    def step(self, action: int):
        act = int(action)
        if act == 0:
            raw_act = [0, 0, 0]
            deployed_kind = None
        else:
            idx = act - 1
            k_idx = idx // self.num_sectors
            sec = idx % self.num_sectors
            tiles = self._sector_tiles[sec]
            if tiles:
                cur = self._sector_cursor[sec]
                x, y = tiles[cur % len(tiles)]
                self._sector_cursor[sec] = cur + 1
                raw_act = [k_idx + 1, x, y]
                deployed_kind = self.troop_keys[k_idx]
            else:
                raw_act = [0, 0, 0]
                deployed_kind = None

        prev_th = self.env.th_destroyed
        obs, reward, term, trunc, info = self.env.step(raw_act)

        if self.shaping_mode == "tactical" and deployed_kind is not None:
            # Small shaping signal for ordering tanks before squishy DPS while troops remain.
            has_giants = self.env.army_left.get("giant_l5", 0) > 0
            if deployed_kind == "giant_l5":
                reward += 0.08
            elif has_giants and deployed_kind in ("archer_l5", "goblin_l5"):
                reward -= 0.03
        if self.shaping_mode == "tactical" and act == 0 and any(self.env.army_left.values()):
            reward -= 0.05

        info = dict(info)
        info["th_destroyed"] = int(self.env.th_destroyed or prev_th)
        return obs, float(reward), term, trunc, info

    def render(self):
        return self.env.render()

    def close(self):
        self.env.close()


class CoCFeatureExtractor(BaseFeaturesExtractor):
    """Lightweight CNN + army MLP extractor tuned for 44x44 CoC grids on CPU."""

    def __init__(self, observation_space: spaces.Dict, features_dim: int = 160):
        super().__init__(observation_space, features_dim)
        grid_shape = observation_space["grid"].shape
        army_dim = int(observation_space["army"].shape[0])
        self.cnn = nn.Sequential(
            nn.Conv2d(grid_shape[0], 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
        )
        self.cnn_head = nn.Sequential(
            nn.Linear(32 * 4 * 4, 128),
            nn.ReLU(),
        )
        self.army_net = nn.Sequential(
            nn.Linear(army_dim, 32),
            nn.ReLU(),
        )

    def forward(self, observations: dict[str, th.Tensor]) -> th.Tensor:
        g = self.cnn_head(self.cnn(observations["grid"]))
        a = self.army_net(observations["army"])
        return th.cat([g, a], dim=1)

