"""Minimal CoC-style attack simulator (Gymnasium). STARTER, not final.

Known simplifications (improve these, see PROJECT_SPEC.md):
  - no walls / pathfinding (troops walk in a straight line)
  - defenses deal continuous dps to the nearest troop in range
  - no spells, heroes, traps, clan castle, splash damage, air troops
  - placeholder stats in data/*.json (see stats_verified flags)
"""
import json
import math
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .entities import Building, Troop

DATA = Path(__file__).resolve().parent.parent / "data"
TICKS_PER_SEC = 10
BATTLE_SECONDS = 180
DEPLOY_MARGIN = 3          # tiles around buildings where deploying is not allowed
ACTION_EVERY_TICKS = 10    # agent acts once per simulated second


def _load(path):
    return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}


class CoCEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, base_file="base01.json", army=None, seed=None, render_mode=None):
        super().__init__()
        self.troop_defs = _load(DATA / "troops.json")
        self.defense_defs = _load(DATA / "defenses.json")
        self.base_cfg = json.load(open(DATA / "bases" / base_file))
        self.grid = self.base_cfg["grid"]
        self.troop_keys = list(self.troop_defs.keys())
        self.army_template = army or {k: 2 if "giant" in k else 6 if "barb" in k else 4 for k in self.troop_keys}
        self.render_mode = render_mode
        n = len(self.troop_keys)
        self.action_space = spaces.MultiDiscrete([n + 1, self.grid, self.grid])  # kind 0 = wait
        self.observation_space = spaces.Dict({
            "grid": spaces.Box(0, 1, (5, self.grid, self.grid), np.float32),
            "army": spaces.Box(0, 1, (n + 2,), np.float32),
        })

    # ------------------------------------------------------------------ setup
    def _load_base(self):
        self.buildings = []
        for b in self.base_cfg["buildings"]:
            d = self.defense_defs[b["type"]]
            self.buildings.append(Building(
                kind=b["type"], x=b["x"], y=b["y"], size=d["size"], hp=d["hp"], max_hp=d["hp"],
                dps=d["dps"], range_tiles=d["range_tiles"], is_defense=d["dps"] > 0,
                is_town_hall=b["type"] == "town_hall"))

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._load_base()
        self.troops = []
        self.tick = 0
        self.army_left = dict(self.army_template)
        self.destruction = 0.0
        self.th_destroyed = False
        return self._obs(), {}

    # -------------------------------------------------------------- mechanics
    def _deployable(self, x, y):
        if not (0 <= x < self.grid and 0 <= y < self.grid):
            return False
        for b in self.buildings:
            if b.x - DEPLOY_MARGIN <= x < b.x + b.size + DEPLOY_MARGIN and \
               b.y - DEPLOY_MARGIN <= y < b.y + b.size + DEPLOY_MARGIN:
                return False
        return True

    def _spawn(self, key, x, y):
        t = self.troop_defs[key]
        self.troops.append(Troop(t["name"], x + .5, y + .5, t["hp"], t["dps"], t["attack_speed"],
                                 t["range_tiles"], t["speed_tiles_per_s"], t["favorite"], t["housing"]))

    def _pick_target(self, tr):
        alive = [b for b in self.buildings if b.alive]
        pool = [b for b in alive if b.is_defense] if tr.favorite == "defenses" else []
        pool = pool or alive
        if not pool:
            return None
        return min(pool, key=lambda b: (b.cx - tr.x) ** 2 + (b.cy - tr.y) ** 2)

    def _sim_tick(self):
        dt = 1 / TICKS_PER_SEC
        for tr in self.troops:
            if not tr.alive:
                continue
            if tr.target is None or not tr.target.alive:
                tr.target = self._pick_target(tr)
            if tr.target is None:
                continue
            dx, dy = tr.target.cx - tr.x, tr.target.cy - tr.y
            d = math.hypot(dx, dy) or 1e-6
            if d - tr.target.size / 2 > tr.range_tiles:
                tr.x += dx / d * tr.speed * dt
                tr.y += dy / d * tr.speed * dt
            else:
                tr.target.hp -= tr.dps * dt
        for b in self.buildings:
            if not (b.alive and b.is_defense):
                continue
            near = [t for t in self.troops if t.alive and math.hypot(t.x - b.cx, t.y - b.cy) <= b.range_tiles]
            if near:
                min(near, key=lambda t: math.hypot(t.x - b.cx, t.y - b.cy)).hp -= b.dps * dt
        self.tick += 1

    def _destruction_now(self):
        # TODO: real CoC excludes walls and weights buildings differently
        bs = [b for b in self.buildings if not b.is_wall]
        return sum(1 for b in bs if not b.alive) / len(bs)

    # ------------------------------------------------------------------- gym
    def step(self, action):
        kind, x, y = int(action[0]), int(action[1]), int(action[2])
        reward = -0.01
        if kind > 0:
            key = self.troop_keys[kind - 1]
            if self.army_left[key] > 0 and self._deployable(x, y):
                self.army_left[key] -= 1
                self._spawn(key, x, y)
            else:
                reward -= 0.05  # invalid deploy
        prev = self.destruction
        for _ in range(ACTION_EVERY_TICKS):
            self._sim_tick()
        self.destruction = self._destruction_now()
        reward += (self.destruction - prev) * 100
        th = next(b for b in self.buildings if b.is_town_hall)
        if not th.alive and not self.th_destroyed:
            self.th_destroyed = True
            reward += 50
        no_troops = not any(self.army_left.values()) and not any(t.alive for t in self.troops)
        terminated = no_troops or self.destruction >= 1.0
        truncated = self.tick >= BATTLE_SECONDS * TICKS_PER_SEC
        stars = int(self.destruction >= .5) + int(self.th_destroyed) + int(self.destruction >= 1.0)
        return self._obs(), reward, terminated, truncated, {"destruction": self.destruction, "stars": stars}

    def _obs(self):
        g = np.zeros((5, self.grid, self.grid), np.float32)
        for b in self.buildings:
            if b.alive:
                xs, ys = int(b.x), int(b.y)
                g[0, ys:ys + b.size, xs:xs + b.size] = b.hp / b.max_hp
                g[1, ys:ys + b.size, xs:xs + b.size] = float(b.is_defense)
                g[2, ys:ys + b.size, xs:xs + b.size] = float(b.is_wall)
        for t in self.troops:
            if t.alive:
                xi = min(self.grid - 1, max(0, int(t.x)))
                yi = min(self.grid - 1, max(0, int(t.y)))
                g[3, yi, xi] = min(1.0, g[3, yi, xi] + 0.25)
        for yy in range(self.grid):
            for xx in range(self.grid):
                g[4, yy, xx] = float(self._deployable(xx, yy))
        army = [self.army_left[k] / max(1, self.army_template[k]) for k in self.troop_keys]
        army += [max(0.0, 1 - self.tick / (BATTLE_SECONDS * TICKS_PER_SEC)), self.destruction]
        return {"grid": g, "army": np.array(army, np.float32)}
