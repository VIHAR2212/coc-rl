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
        self._wall_hp_grid = np.zeros((self.grid, self.grid), dtype=np.float32)
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
                self._wall_hp_grid[int(bld.y), int(bld.x)] = 1.0
            x0, x1 = max(0, int(bld.x) - DEPLOY_MARGIN), min(self.grid, int(bld.x) + bld.size + DEPLOY_MARGIN)
            y0, y1 = max(0, int(bld.y) - DEPLOY_MARGIN), min(self.grid, int(bld.y) + bld.size + DEPLOY_MARGIN)
            self._deploy_mask[y0:y1, x0:x1] = 0.0
        self._non_walls = [b for b in self.buildings if not b.is_wall]
        self._defenses = [b for b in self.buildings if b.is_defense]

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._load_base()
        for b in self._defenses:
            b.cooldown = float(self.np_random.uniform(0.0, b.attack_speed))
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
        jx = float(self.np_random.uniform(-0.3, 0.3))
        jy = float(self.np_random.uniform(-0.3, 0.3))
        self.troops.append(Troop(
            t["name"], x + 0.5 + jx, y + 0.5 + jy, t["hp"], t["dps"], t["attack_speed"],
            t["range_tiles"], t["speed_tiles_per_s"], t["favorite"], t["housing"],
            damage_vs_walls=t.get("damage_vs_walls", 0.0),
            splash_radius=t.get("splash_radius", 0.0),
            is_flying=bool(t.get("is_flying", False)),
            wall_jumper=bool(t.get("wall_jumper", False)),
            whirlwind=bool(t.get("whirlwind", False)),
            death_damage=float(t.get("death_damage", 0.0)),
            death_splash_radius=float(t.get("death_splash_radius", 0.0)),
            splits_into=int(t.get("splits_into", 0)),
            split_troop=str(t.get("split_troop", "")),
        ))

    def _pick_target(self, tr):
        non_walls = [b for b in self._non_walls if b.hp > 0]
        if tr.favorite == "walls":
            walls = [b for b in self.buildings if b.hp > 0 and b.is_wall]
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
        if bld.hp <= 0:
            return
        bld.hp -= dmg
        if bld.is_wall:
            wx, wy = int(bld.x), int(bld.y)
            self._wall_hp_grid[wy, wx] = bld.hp / bld.max_hp if bld.hp > 0 else 0.0
            if bld.hp <= 0 and self._wall_grid[wy, wx]:
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
                step_dist = tr.speed * dt
                if tr.is_flying or tr.wall_jumper:
                    tr.x += dx / d * step_dist
                    tr.y += dy / d * step_dist
                else:
                    if tr.path_target_id != id(tr.target) or tr.path_wall_ver != self._wall_version:
                        path = self._get_path(tr, tr.target)
                        if path is None and not tr.target.is_wall:
                            walls = [b for b in self.buildings if b.hp > 0 and b.is_wall]
                            if walls:
                                tx, ty = tr.x, tr.y
                                tcx, tcy = tr.target.cx, tr.target.cy
                                hypot = math.hypot
                                wall = min(
                                    walls,
                                    key=lambda w: hypot(w.cx - tx, w.cy - ty) + 0.5 * hypot(w.cx - tcx, w.cy - tcy),
                                )
                                tr.target = wall
                                path = self._get_path(tr, wall)
                                dx, dy = tr.target.cx - tr.x, tr.target.cy - tr.y
                                d = math.hypot(dx, dy) or 1e-6
                        tr.path = path or []
                        tr.path_wall_ver = self._wall_version
                        tr.path_target_id = id(tr.target)
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
                elif tr.whirlwind:
                    tx, ty = tr.x, tr.y
                    rad = tr.splash_radius or 1.0
                    dmg = tr.dps * dt
                    for b in self.buildings:
                        if b.alive:
                            bx = min(max(tx, b.x), b.x + b.size)
                            by = min(max(ty, b.y), b.y + b.size)
                            if math.hypot(bx - tx, by - ty) <= rad:
                                self._damage_building(b, dmg)
                elif tr.splash_radius > 0:
                    tgt = tr.target
                    rad = tr.splash_radius
                    dmg = tr.dps * dt
                    self._damage_building(tgt, dmg)
                    for b in self.buildings:
                        if b.alive and b is not tgt:
                            dx = max(0.0, max(b.x - (tgt.x + tgt.size), tgt.x - (b.x + b.size)))
                            dy = max(0.0, max(b.y - (tgt.y + tgt.size), tgt.y - (b.y + b.size)))
                            if math.hypot(dx, dy) <= rad:
                                self._damage_building(b, dmg)
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

        troops = self.troops
        any_flying = any(t.is_flying for t in troops)
        for b in self._defenses:
            if b.hp <= 0:
                continue
            if b.cooldown > 0.0:
                b.cooldown -= dt
            if b.cooldown > 1e-9:
                continue
            bt = b.targets
            if bt == "air" and not any_flying:
                b.cooldown = 0.0
                continue
            min_r2 = b.min_range_tiles * b.min_range_tiles
            r2 = b.range_tiles * b.range_tiles
            best_t, best_d2 = None, r2
            bcx, bcy = b.cx, b.cy
            if not any_flying:
                for t in troops:
                    if t.hp <= 0:
                        continue
                    d2 = (t.x - bcx) ** 2 + (t.y - bcy) ** 2
                    if min_r2 <= d2 <= best_d2:
                        best_d2 = d2
                        best_t = t
            else:
                for t in troops:
                    if t.hp <= 0 or not self._targets_match(bt, t):
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
                    targets=bt,
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
        new_troops = []
        for t in troops:
            if t.hp <= 0:
                if t.death_damage > 0:
                    rad = t.death_splash_radius or 1.2
                    for b in self.buildings:
                        if b.alive:
                            bx = min(max(t.x, b.x), b.x + b.size)
                            by = min(max(t.y, b.y), b.y + b.size)
                            if math.hypot(bx - t.x, by - t.y) <= rad:
                                self._damage_building(b, t.death_damage)
                if t.splits_into > 0 and t.split_troop in self.troop_defs:
                    sdef = self.troop_defs[t.split_troop]
                    for s_idx in range(t.splits_into):
                        soff = 0.35 if s_idx == 0 else -0.35
                        new_troops.append(Troop(
                            sdef["name"], t.x + soff, t.y + soff,
                            sdef["hp"], sdef["dps"], sdef["attack_speed"],
                            sdef["range_tiles"], sdef["speed_tiles_per_s"],
                            sdef["favorite"], sdef["housing"],
                            damage_vs_walls=sdef.get("damage_vs_walls", 0.0),
                            splash_radius=sdef.get("splash_radius", 0.0),
                            is_flying=bool(sdef.get("is_flying", False)),
                            wall_jumper=bool(sdef.get("wall_jumper", False)),
                            whirlwind=bool(sdef.get("whirlwind", False)),
                            death_damage=float(sdef.get("death_damage", 0.0)),
                            death_splash_radius=float(sdef.get("death_splash_radius", 0.0)),
                            splits_into=int(sdef.get("splits_into", 0)),
                            split_troop=str(sdef.get("split_troop", "")),
                        ))
        alive = [t for t in troops if t.hp > 0]
        alive.extend(new_troops)
        self.troops = alive
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
        g[0] = self._wall_hp_grid
        g[2] = self._wall_grid
        for b in self._non_walls:
            if b.hp > 0:
                xs, ys = int(b.x), int(b.y)
                g[0, ys:ys + b.size, xs:xs + b.size] = b.hp / b.max_hp
                g[1, ys:ys + b.size, xs:xs + b.size] = float(b.is_defense)
        for t in self.troops:
            if t.hp > 0:
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
            "Wall Breaker": (240, 240, 245), "Goblin": (70, 235, 90),
            "Wizard": (70, 150, 255), "Valkyrie": (225, 60, 40), "Hog Rider": (165, 95, 45),
            "Golem": (80, 75, 75), "Golemite": (140, 135, 135), "Dragon": (185, 55, 215),
            "Balloon": (210, 45, 45), "Minion": (45, 195, 235),
        }
        t_radii = {
            "Giant": 9, "Barbarian": 6, "Archer": 5, "Wall Breaker": 5, "Goblin": 5,
            "Wizard": 6, "Valkyrie": 7, "Hog Rider": 7,
            "Golem": 11, "Golemite": 6, "Dragon": 10,
            "Balloon": 7, "Minion": 5,
        }
        for tr in self.troops:
            if tr.alive:
                pos = (int(tr.x * cell), int(tr.y * cell))
                rad = t_radii.get(tr.name, 5)
                col = t_colors.get(tr.name, (255, 255, 255))
                name = tr.name
                if name == "Golem" or name == "Golemite":
                    rect = pg.Rect(pos[0] - rad, pos[1] - rad, rad * 2, rad * 2)
                    pg.draw.rect(surf, col, rect)
                    pg.draw.rect(surf, (20, 20, 20), rect, 1)
                elif name == "Dragon":
                    pts = [(pos[0], pos[1] - rad), (pos[0] + rad, pos[1]), (pos[0], pos[1] + rad), (pos[0] - rad, pos[1])]
                    pg.draw.polygon(surf, col, pts)
                    pg.draw.polygon(surf, (20, 20, 20), pts, 1)
                elif name == "Minion":
                    pts = [(pos[0], pos[1] - rad), (pos[0] + rad, pos[1] + rad), (pos[0] - rad, pos[1] + rad)]
                    pg.draw.polygon(surf, col, pts)
                    pg.draw.polygon(surf, (20, 20, 20), pts, 1)
                elif name == "Balloon":
                    pg.draw.circle(surf, col, pos, rad)
                    pg.draw.circle(surf, (20, 20, 20), pos, rad, 1)
                    pg.draw.rect(surf, (80, 40, 20), (pos[0] - 2, pos[1] + rad, 4, 3))
                elif name == "Wall Breaker":
                    pg.draw.circle(surf, col, pos, rad)
                    pg.draw.circle(surf, (20, 20, 20), pos, rad, 1)
                    pg.draw.circle(surf, (40, 40, 40), pos, 2)
                else:
                    pg.draw.circle(surf, col, pos, rad)
                    pg.draw.circle(surf, (20, 20, 20), pos, rad, 1)

                if tr.max_hp > 0 and tr.hp < tr.max_hp:
                    bar_w = max(8, rad * 2)
                    bar_h = 2
                    bx = pos[0] - bar_w // 2
                    by = pos[1] - rad - 4
                    frac = max(0.0, min(1.0, tr.hp / tr.max_hp))
                    pg.draw.rect(surf, (30, 30, 30), (bx, by, bar_w, bar_h))
                    pg.draw.rect(surf, (80, 230, 80), (bx, by, int(bar_w * frac), bar_h))

        stars = int(self.destruction >= 0.5) + int(self.th_destroyed) + int(self.destruction >= 1.0)
        rem = max(0.0, BATTLE_SECONDS - self.tick / TICKS_PER_SEC)
        alive_count = sum(1 for tr in self.troops if tr.alive)
        dep_count = sum(self.army_template.values()) - sum(self.army_left.values())
        hud = self._font.render(
            f"time left: {rem:5.1f}s  dest={self.destruction*100:5.1f}%  stars={stars}  troops: {alive_count}/{dep_count}",
            True,
            (255, 255, 255),
        )
        pg.draw.rect(surf, (20, 25, 20), (4, 4, hud.get_width() + 10, hud.get_height() + 6))
        surf.blit(hud, (9, 7))

        # Troop legend in bottom-left covering all troop types
        all_legend = {
            "Giant": ("Giant", (245, 140, 40), 6, "circle"),
            "Barbarian": ("Barb", (250, 225, 65), 5, "circle"),
            "Archer": ("Arch", (235, 85, 175), 4, "circle"),
            "Wall Breaker": ("WB", (240, 240, 245), 4, "wb"),
            "Goblin": ("Gobl", (70, 235, 90), 4, "circle"),
            "Wizard": ("Wiz", (70, 150, 255), 5, "circle"),
            "Valkyrie": ("Valk", (225, 60, 40), 5, "circle"),
            "Hog Rider": ("Hog", (165, 95, 45), 5, "circle"),
            "Golem": ("Gol", (80, 75, 75), 6, "square"),
            "Golemite": ("Glmt", (140, 135, 135), 4, "square"),
            "Dragon": ("Drag", (185, 55, 215), 6, "diamond"),
            "Balloon": ("Loon", (210, 45, 45), 5, "balloon"),
            "Minion": ("Min", (45, 195, 235), 4, "triangle"),
        }

        active_names = [self.troop_defs[k]["name"] for k, cnt in self.army_template.items() if cnt > 0]
        if "Golem" in active_names:
            active_names.append("Golemite")
        display_names = [n for n in all_legend if n in active_names] if active_names else list(all_legend.keys())
        leg_items = [all_legend[n] for n in display_names if n in all_legend]

        leg_x, leg_y = 6, size_px - 22
        total_leg_w = min(size_px - 10, max(280, sum(rad * 2 + len(lbl) * 8 + 16 for lbl, _, rad, _ in leg_items) + 12))
        pg.draw.rect(surf, (20, 25, 20), (4, size_px - 26, total_leg_w, 22))
        for lbl, col, rad, shape in leg_items:
            center = (leg_x + rad, leg_y + 8)
            if shape == "square":
                pg.draw.rect(surf, col, (center[0] - rad, center[1] - rad, rad * 2, rad * 2))
                pg.draw.rect(surf, (20, 20, 20), (center[0] - rad, center[1] - rad, rad * 2, rad * 2), 1)
            elif shape == "diamond":
                pts = [(center[0], center[1] - rad), (center[0] + rad, center[1]), (center[0], center[1] + rad), (center[0] - rad, center[1])]
                pg.draw.polygon(surf, col, pts)
                pg.draw.polygon(surf, (20, 20, 20), pts, 1)
            elif shape == "triangle":
                pts = [(center[0], center[1] - rad), (center[0] + rad, center[1] + rad), (center[0] - rad, center[1] + rad)]
                pg.draw.polygon(surf, col, pts)
                pg.draw.polygon(surf, (20, 20, 20), pts, 1)
            elif shape == "balloon":
                pg.draw.circle(surf, col, center, rad)
                pg.draw.circle(surf, (20, 20, 20), center, rad, 1)
                pg.draw.rect(surf, (80, 40, 20), (center[0] - 2, center[1] + rad, 4, 2))
            elif shape == "wb":
                pg.draw.circle(surf, col, center, rad)
                pg.draw.circle(surf, (20, 20, 20), center, rad, 1)
                pg.draw.circle(surf, (40, 40, 40), center, 2)
            else:
                pg.draw.circle(surf, col, center, rad)
                pg.draw.circle(surf, (20, 20, 20), center, rad, 1)
            ltxt = self._font.render(lbl, True, (230, 230, 230))
            surf.blit(ltxt, (leg_x + rad * 2 + 4, leg_y + 1))
            leg_x += rad * 2 + ltxt.get_width() + 14

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
