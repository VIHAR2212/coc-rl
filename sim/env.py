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

from .entities import Building, PendingProjectile, Troop
from .pathing import astar_path

DATA = Path(__file__).resolve().parent.parent / "data"
TICKS_PER_SEC = 10
BATTLE_SECONDS = 180
DEPLOY_MARGIN = 3          # tiles around buildings where deploying is not allowed
ACTION_EVERY_TICKS = 10    # agent acts once per simulated second


def _load(path):
    return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}


ARMY_LIMIT = int(json.loads((DATA / "armies.json").read_text(encoding="utf-8"))["_housing_capacity"])


class CoCEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, base_file="base01.json", army=None, seed=None, render_mode=None):
        super().__init__()
        self.troop_defs = _load(DATA / "troops.json")
        self.defense_defs = _load(DATA / "defenses.json")
        self.army_defs = _load(DATA / "armies.json")
        self.army_limit = ARMY_LIMIT
        self.base_cfg = json.load(open(DATA / "bases" / base_file))
        self.grid = self.base_cfg["grid"]
        self.troop_keys = list(self.troop_defs.keys())
        self.army_template = self._resolve_army(army)
        self.render_mode = render_mode
        self._screen = None
        self._surface = None
        self._font = None
        self._pygame = None
        n = len(self.troop_keys)
        self.action_space = spaces.MultiDiscrete([n + 1, self.grid, self.grid])  # kind 0 = wait
        self.observation_space = spaces.Dict({
            "grid": spaces.Box(0, 1, (5, self.grid, self.grid), np.float32),
            "army": spaces.Box(0, 1, (n + 2,), np.float32),
        })

    def _resolve_army(self, army):
        if army is None:
            raw = self.army_defs[next(iter(self.army_defs))]
        elif isinstance(army, str):
            if army not in self.army_defs:
                raise ValueError(f"Unknown army {army!r}; available: {list(self.army_defs)}")
            raw = self.army_defs[army]
        else:
            raw = army
        total_housing = 0
        for k, count in raw.items():
            if k not in self.troop_defs:
                raise ValueError(f"Unknown troop key {k!r} in army")
            if int(count) < 0:
                raise ValueError(f"Negative count for troop {k!r}: {count}")
            total_housing += int(count) * self.troop_defs[k]["housing"]
        if total_housing > self.army_limit:
            raise ValueError(f"Army housing {total_housing} exceeds limit {self.army_limit}")
        return {k: int(raw.get(k, 0)) for k in self.troop_keys}

    # ------------------------------------------------------------------ setup
    def _load_base(self):
        self.buildings = []
        self._deploy_mask = np.ones((self.grid, self.grid), dtype=np.float32)
        self._wall_grid = np.zeros((self.grid, self.grid), dtype=bool)
        self._wall_version = 0
        self._path_cache = {}
        self.projectiles = []
        for b in self.base_cfg["buildings"]:
            d = self.defense_defs[b["type"]]
            is_wall = b["type"] == "wall"
            bld = Building(
                kind=b["type"], x=b["x"], y=b["y"], size=d["size"], hp=d["hp"], max_hp=d["hp"],
                dps=d["dps"], range_tiles=d["range_tiles"],
                attack_speed=d.get("attack_speed", 1.0) or 1.0,
                min_range_tiles=d.get("min_range_tiles", 0.0),
                splash_radius=d.get("splash_radius", 0.0),
                targets=d.get("targets", "ground"),
                # TODO: projectile_delay is missing from Fandom wiki / coc.guide tables (see data/DISCREPANCIES.md)
                projectile_delay=d.get("projectile_delay", 0.0),
                is_defense=d["dps"] > 0, is_wall=is_wall, is_town_hall=b["type"] == "town_hall")
            self.buildings.append(bld)
            if is_wall:
                self._wall_grid[int(bld.y), int(bld.x)] = True
            x0, x1 = max(0, int(bld.x) - DEPLOY_MARGIN), min(self.grid, int(bld.x) + bld.size + DEPLOY_MARGIN)
            y0, y1 = max(0, int(bld.y) - DEPLOY_MARGIN), min(self.grid, int(bld.y) + bld.size + DEPLOY_MARGIN)
            self._deploy_mask[y0:y1, x0:x1] = 0.0
        self._non_walls = [b for b in self.buildings if not b.is_wall]
        self._defenses = [b for b in self.buildings if b.is_defense]

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._load_base()
        self.troops = []
        self.projectiles = []
        self.tick = 0
        self.army_left = dict(self.army_template)
        self.destruction = 0.0
        self.th_destroyed = False
        return self._obs(), {}

    # -------------------------------------------------------------- mechanics
    def _deployable(self, x, y):
        return 0 <= x < self.grid and 0 <= y < self.grid and bool(self._deploy_mask[y, x])

    def _spawn(self, key, x, y):
        t = self.troop_defs[key]
        self.troops.append(Troop(
            t["name"], x + .5, y + .5, t["hp"], t["dps"], t["attack_speed"],
            t["range_tiles"], t["speed_tiles_per_s"], t["favorite"], t["housing"],
            damage_vs_walls=t.get("damage_vs_walls", 0.0),
            splash_radius=t.get("splash_radius", 0.0),
            is_flying=bool(t.get("is_flying", False)),
        ))

    def _pick_target(self, tr):
        non_walls = [b for b in self.buildings if b.alive and not b.is_wall]
        if tr.favorite == "walls":
            walls = [b for b in self.buildings if b.alive and b.is_wall]
            pool = walls or non_walls
        elif tr.favorite == "defenses":
            pool = [b for b in non_walls if b.is_defense] or non_walls
        elif tr.favorite == "resources":
            pool = [b for b in non_walls if "storage" in b.kind] or non_walls
        else:
            pool = non_walls
        if not pool:
            return None
        return min(pool, key=lambda b: (b.cx - tr.x) ** 2 + (b.cy - tr.y) ** 2)

    def _damage_building(self, bld, dmg):
        if not bld.alive:
            return
        bld.hp -= dmg
        if bld.hp <= 0 and bld.is_wall:
            wx, wy = int(bld.x), int(bld.y)
            if self._wall_grid[wy, wx]:
                self._wall_grid[wy, wx] = False
                self._wall_version += 1
                self._path_cache.clear()

    def _get_path(self, tr, target):
        key = (int(tr.x), int(tr.y), id(target), round(tr.range_tiles, 2))
        if key not in self._path_cache:
            self._path_cache[key] = astar_path(
                self._wall_grid, (int(tr.x), int(tr.y)),
                target.cx, target.cy, target.size, tr.range_tiles,
            )
        cached = self._path_cache[key]
        return None if cached is None else list(cached)

    @staticmethod
    def _targets_match(targets: str, tr: Troop) -> bool:
        if targets == "air_ground":
            return True
        if targets == "air":
            return tr.is_flying
        if targets == "ground":
            return not tr.is_flying
        return False

    def _resolve_projectile(self, p: PendingProjectile) -> None:
        if p.splash_radius > 0:
            r2 = p.splash_radius * p.splash_radius
            for t in self.troops:
                if t.alive and self._targets_match(p.targets, t):
                    if (t.x - p.x) ** 2 + (t.y - p.y) ** 2 <= r2:
                        t.hp -= p.damage
        elif p.target is not None and p.target.alive:
            p.target.hp -= p.damage

    def _sim_tick(self):
        dt = 1 / TICKS_PER_SEC
        for tr in self.troops:
            if not tr.alive:
                continue
            if tr.target is not None and tr.target.is_wall and tr.favorite != "walls" and tr.path_wall_ver != self._wall_version:
                tr.target = None
            if tr.target is None or not tr.target.alive:
                tr.target = self._pick_target(tr)
                tr.path = []
                tr.path_target_id = -1
            if tr.target is None:
                continue
            dx, dy = tr.target.cx - tr.x, tr.target.cy - tr.y
            d = math.hypot(dx, dy) or 1e-6
            if d - tr.target.size / 2 > tr.range_tiles:
                if tr.path_target_id != id(tr.target) or tr.path_wall_ver != self._wall_version:
                    path = self._get_path(tr, tr.target)
                    if path is None and not tr.target.is_wall:
                        walls = [b for b in self.buildings if b.alive and b.is_wall]
                        if walls:
                            wall = min(
                                walls,
                                key=lambda w: math.hypot(w.cx - tr.x, w.cy - tr.y)
                                + 0.5 * math.hypot(w.cx - tr.target.cx, w.cy - tr.target.cy),
                            )
                            tr.target = wall
                            path = self._get_path(tr, wall)
                            dx, dy = tr.target.cx - tr.x, tr.target.cy - tr.y
                            d = math.hypot(dx, dy) or 1e-6
                    tr.path = path or []
                    tr.path_wall_ver = self._wall_version
                    tr.path_target_id = id(tr.target)
                step_dist = tr.speed * dt
                if tr.path:
                    wx, wy = tr.path[0]
                    wdx, wdy = wx - tr.x, wy - tr.y
                    wd = math.hypot(wdx, wdy)
                    if wd <= max(0.15, step_dist):
                        tr.x, tr.y = wx, wy
                        tr.path.pop(0)
                    else:
                        tr.x += wdx / wd * step_dist
                        tr.y += wdy / wd * step_dist
                else:
                    tr.x += dx / d * step_dist
                    tr.y += dy / d * step_dist
            else:
                if tr.favorite == "walls" and tr.damage_vs_walls > 0:
                    tx, ty = tr.target.cx, tr.target.cy
                    rad = tr.splash_radius or 2.0
                    for b in list(self.buildings):
                        if b.alive and math.hypot(b.cx - tx, b.cy - ty) <= rad:
                            self._damage_building(b, tr.damage_vs_walls if b.is_wall else tr.dps)
                    tr.hp = 0.0
                else:
                    self._damage_building(tr.target, tr.dps * dt)
        still_flying = []
        for p in self.projectiles:
            p.delay_left -= dt
            if p.delay_left <= 1e-9:
                self._resolve_projectile(p)
            else:
                still_flying.append(p)
        self.projectiles = still_flying

        for b in self._defenses:
            if not b.alive:
                continue
            if b.cooldown > 0.0:
                b.cooldown -= dt
            if b.cooldown > 1e-9:
                continue
            min_r2 = b.min_range_tiles * b.min_range_tiles
            r2 = b.range_tiles * b.range_tiles
            best_t, best_d2 = None, r2
            bcx, bcy = b.cx, b.cy
            for t in self.troops:
                if not t.alive or not self._targets_match(b.targets, t):
                    continue
                d2 = (t.x - bcx) ** 2 + (t.y - bcy) ** 2
                if min_r2 <= d2 <= best_d2:
                    best_d2 = d2
                    best_t = t
            if best_t is not None:
                shot = PendingProjectile(
                    x=best_t.x,
                    y=best_t.y,
                    damage=b.dps * b.attack_speed,
                    splash_radius=b.splash_radius,
                    targets=b.targets,
                    delay_left=b.projectile_delay,
                    target=None if b.splash_radius > 0 else best_t,
                )
                if shot.delay_left <= 1e-9:
                    self._resolve_projectile(shot)
                else:
                    self.projectiles.append(shot)
                b.cooldown += b.attack_speed
            else:
                b.cooldown = 0.0
        self.troops = [t for t in self.troops if t.alive]
        self.tick += 1

    def _destruction_now(self):
        return sum(1 for b in self._non_walls if not b.alive) / len(self._non_walls)

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
        g[4] = self._deploy_mask
        army = [self.army_left[k] / max(1, self.army_template[k]) for k in self.troop_keys]
        army += [max(0.0, 1 - self.tick / (BATTLE_SECONDS * TICKS_PER_SEC)), self.destruction]
        return {"grid": g, "army": np.array(army, np.float32)}

    # ---------------------------------------------------------------- render
    def render(self):
        if self.render_mode is None:
            return None
        if self._pygame is None:
            import pygame
            pygame.init()
            self._pygame = pygame
            self._font = pygame.font.SysFont("consolas", 13, bold=True)
        pg = self._pygame
        cell = 14
        size_px = self.grid * cell
        if self._surface is None:
            self._surface = pg.Surface((size_px, size_px))
        if self.render_mode == "human" and self._screen is None:
            self._screen = pg.display.set_mode((size_px, size_px))
            pg.display.set_caption("coc-rl")

        surf = self._surface
        surf.fill((96, 158, 64))
        for yy in range(self.grid):
            for xx in range(self.grid):
                if self._deploy_mask[yy, xx] == 0:
                    pg.draw.rect(surf, (80, 132, 54), (xx * cell, yy * cell, cell, cell))
        for i in range(0, self.grid + 1):
            p = i * cell
            pg.draw.line(surf, (84, 140, 56), (p, 0), (p, size_px), 1)
            pg.draw.line(surf, (84, 140, 56), (0, p), (size_px, p), 1)

        colors = {
            "town_hall": (218, 170, 52), "cannon": (182, 62, 62), "archer_tower": (210, 102, 58),
            "mortar": (118, 122, 138), "air_defense": (86, 134, 200), "wizard_tower": (152, 82, 188),
            "gold_storage": (205, 185, 78), "elixir_storage": (196, 86, 168), "storage": (196, 140, 96),
            "wall": (150, 150, 150),
        }
        labels = {
            "town_hall": "TH", "cannon": "CN", "archer_tower": "AT", "mortar": "MT",
            "air_defense": "AD", "wizard_tower": "WT", "gold_storage": "GS",
            "elixir_storage": "ES", "storage": "ST", "wall": "",
        }
        for b in self.buildings:
            rect = pg.Rect(int(b.x * cell), int(b.y * cell), int(b.size * cell), int(b.size * cell))
            if not b.alive:
                pg.draw.rect(surf, (66, 94, 52), rect, 1)
                continue
            pg.draw.rect(surf, colors.get(b.kind, (160, 160, 160)), rect)
            pg.draw.rect(surf, (35, 35, 35), rect, 2)
            lbl = labels.get(b.kind, b.kind[:2].upper())
            if lbl and b.size >= 2:
                txt = self._font.render(lbl, True, (255, 255, 255))
                surf.blit(txt, txt.get_rect(center=rect.center))
            if b.hp < b.max_hp:
                frac = max(0.0, min(1.0, b.hp / b.max_hp))
                pg.draw.rect(surf, (40, 40, 40), (rect.x + 2, rect.y + 2, rect.w - 4, 4))
                pg.draw.rect(surf, (80, 230, 80), (rect.x + 2, rect.y + 2, int((rect.w - 4) * frac), 4))

        t_colors = {
            "Giant": (245, 140, 40), "Barbarian": (250, 225, 65), "Archer": (235, 85, 175),
            "Wall Breaker": (235, 235, 240), "Goblin": (70, 235, 90),
        }
        for tr in self.troops:
            if tr.alive:
                pos = (int(tr.x * cell), int(tr.y * cell))
                rad = 6 if tr.name == "Giant" else 4
                pg.draw.circle(surf, t_colors.get(tr.name, (255, 255, 255)), pos, rad)
                pg.draw.circle(surf, (20, 20, 20), pos, rad, 1)

        stars = int(self.destruction >= 0.5) + int(self.th_destroyed) + int(self.destruction >= 1.0)
        rem = max(0.0, BATTLE_SECONDS - self.tick / TICKS_PER_SEC)
        hud = self._font.render(f"t={rem:5.1f}s  dest={self.destruction*100:5.1f}%  stars={stars}", True, (255, 255, 255))
        pg.draw.rect(surf, (20, 25, 20), (4, 4, hud.get_width() + 10, hud.get_height() + 6))
        surf.blit(hud, (9, 7))

        if self.render_mode == "human":
            self._screen.blit(surf, (0, 0))
            pg.event.pump()
            pg.display.flip()
            return None
        return np.transpose(pg.surfarray.array3d(surf), (1, 0, 2)).copy()

    def close(self):
        if self._pygame is not None:
            if self._screen is not None:
                self._pygame.display.quit()
                self._screen = None
            self._surface = None
            self._pygame.quit()
            self._pygame = None
