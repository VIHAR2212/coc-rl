"""Gymnasium wrapper adding valid-edge sector actions, TH grid channel, and action masks."""
import json
import math
from pathlib import Path
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
# Exclude trivial base01.json from RL training split (M7b).
TRAIN_BASES = ["base02.json", "base03.json", "base04.json"]
HELD_OUT_BASES = [
    "base05.json",
    "base06.json",
    "base07.json",
    "base08.json",
    "base09.json",
    "base10.json",
]


class ActionMaskCoCEnv(gym.Env):
    """Wraps CoCEnv with discrete (troop, edge-sector) actions, TH channel, and validity masks."""

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        bases: list[str] | str = "base03.json",
        armies: list[str] | str | None = None,
        num_sectors: int = NUM_SECTORS,
        shaping_mode: str = "stars_aware",
        render_mode: str | None = None,
    ):
        super().__init__()
        self.base_pool = [bases] if isinstance(bases, str) else list(bases)
        if armies is None:
            raw_armies = json.loads((Path(__file__).resolve().parent.parent / "data" / "armies.json").read_text(encoding="utf-8"))
            self.army_pool = [k for k in raw_armies if not k.startswith("_")]
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
        grid_shape = self.env.observation_space["grid"].shape
        self.observation_space = spaces.Dict({
            # Add 6th channel highlighting the Town Hall footprint so RL can aim for the TH star.
            "grid": spaces.Box(0, 1, (grid_shape[0] + 1, grid_shape[1], grid_shape[2]), np.float32),
            "army": self.env.observation_space["army"],
        })

        self._sector_tiles: list[list[tuple[int, int]]] = [[] for _ in range(self.num_sectors)]
        self._sector_cursor: list[int] = [0] * self.num_sectors
        self._th_grid = np.zeros((1, self.env.grid, self.env.grid), dtype=np.float32)
        self._ep_idx = 0
        self._unique_sectors: set[int] = set()
        self._sector_deploy_counts: list[int] = [0] * self.num_sectors

    def _rebuild_sectors(self) -> None:
        ring = edge_ring_tiles(self.env)
        buckets: list[list[tuple[int, int]]] = [[] for _ in range(self.num_sectors)]
        mid = self.env.grid / 2.0
        for x, y in ring:
            ang = math.atan2(y - mid, x - mid)
            frac = (ang + math.pi) / (2.0 * math.pi)
            sec = min(self.num_sectors - 1, max(0, int(frac * self.num_sectors)))
            buckets[sec].append((x, y))
        self._sector_tiles = buckets
        self._sector_cursor = [0] * self.num_sectors

    def _build_th_grid(self) -> None:
        self._th_grid.fill(0.0)
        for b in self.env._non_walls:
            if b.is_town_hall and b.hp > 0:
                xs, ys = int(b.x), int(b.y)
                self._th_grid[0, ys:ys + b.size, xs:xs + b.size] = b.hp / b.max_hp

    def _wrap_obs(self, obs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        self._build_th_grid()
        return {
            "grid": np.concatenate([obs["grid"], self._th_grid], axis=0),
            "army": obs["army"],
        }

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
        self._unique_sectors = set()
        self._sector_deploy_counts = [0] * self.num_sectors
        info = dict(info)
        info.update({"base": chosen_base, "army": chosen_army})
        return self._wrap_obs(obs), info

    def action_masks(self) -> np.ndarray:
        mask = np.zeros(1 + self.n_troops * self.num_sectors, dtype=bool)
        has_army = any(self.env.army_left[k] > 0 for k in self.troop_keys)
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
            else:
                raw_act = [0, 0, 0]

        prev_dest = self.env.destruction
        prev_th = self.env.th_destroyed
        obs, reward, term, trunc, info = self.env.step(raw_act)

        if act > 0:
            idx = act - 1
            sec = idx % self.num_sectors
            if sec not in self._unique_sectors:
                self._unique_sectors.add(sec)
                # Anti-collapse bonus: reward spreading attack across multiple sectors
                reward += 0.5
            self._sector_deploy_counts[sec] += 1
            tot = sum(self._sector_deploy_counts)
            # Anti-collapse penalty: discourage single-sector clumping (>50% troops in 1 sector)
            if tot > 10 and (self._sector_deploy_counts[sec] / tot) > 0.5:
                reward -= 0.1

        if self.shaping_mode == "stars_aware":
            # Bonus for crossing 50% (1 star), Town Hall (+25 on top of +50 = +75), and 100% (3 stars).
            if prev_dest < 0.5 <= self.env.destruction:
                reward += 25.0
            if not prev_th and self.env.th_destroyed:
                reward += 25.0
            if prev_dest < 1.0 <= self.env.destruction:
                reward += 50.0
            if act == 0 and any(self.env.army_left.values()):
                reward -= 0.05

        info = dict(info)
        info["th_destroyed"] = int(self.env.th_destroyed)
        return self._wrap_obs(obs), float(reward), term, trunc, info

    def render(self):
        return self.env.render()

    def close(self):
        self.env.close()


class CoCFeatureExtractor(BaseFeaturesExtractor):
    """Lightweight stride-4 CNN + army MLP extractor tuned for 44x44 CoC grids on CPU."""

    def __init__(self, observation_space: spaces.Dict, features_dim: int = 128):
        super().__init__(observation_space, features_dim)
        grid_shape = observation_space["grid"].shape
        army_dim = int(observation_space["army"].shape[0])
        self.cnn = nn.Sequential(
            nn.Conv2d(grid_shape[0], 16, kernel_size=4, stride=4),
            nn.ReLU(),
            nn.Conv2d(16, 24, kernel_size=3, stride=2),
            nn.ReLU(),
            nn.Flatten(),
        )
        with th.no_grad():
            n_flat = self.cnn(th.zeros(1, *grid_shape)).shape[1]
        self.head = nn.Sequential(
            nn.Linear(n_flat + army_dim, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations: dict[str, th.Tensor]) -> th.Tensor:
        return self.head(th.cat([self.cnn(observations["grid"]), observations["army"]], dim=1))
