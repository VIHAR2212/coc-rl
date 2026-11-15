"""Procedural TH8 base generator for Clash of Clans RL environment.

Generates deterministic, valid TH8 base layouts conforming to:
- 44x44 grid bounds
- Zero footprint overlaps
- Realistic TH8 building limits (from data/raw/Town_Hall.json and data/defenses.json):
  * town_hall: 1 (4x4)
  * cannon: 5 (3x3)
  * archer_tower: 5 (3x3)
  * mortar: 4 (3x3)
  * air_defense: 3 (3x3)
  * wizard_tower: 3 (3x3)
  * hidden_tesla: 3 (2x2)
  * bomb_tower: 1 (3x3)
  * gold_storage: 3 (3x3)
  * elixir_storage: 3 (3x3)
  * wall: <= 225 (1x1)
- Multiple tactical layout styles:
  * compartmented (concentric rings / multi-compartment)
  * clustered_core (dense central core with radial perimeter defenses)
  * spread_out (open layout with spaced defense islands)
  * defenses_outside (storages/TH interior, defenses on outer perimeter)
  * asymmetric (off-center TH with opposite defense bastion)
  * mixed (hybrid compartment + open funnel lanes)
  * open_no_walls (open field without walls)
"""

import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

STYLES = [
    "compartmented",
    "clustered_core",
    "spread_out",
    "defenses_outside",
    "asymmetric",
    "mixed",
    "open_no_walls",
]

BUILDING_SIZES = {
    "town_hall": 4,
    "cannon": 3,
    "archer_tower": 3,
    "mortar": 3,
    "air_defense": 3,
    "wizard_tower": 3,
    "bomb_tower": 3,
    "gold_storage": 3,
    "elixir_storage": 3,
    "hidden_tesla": 2,
    "wall": 1,
}

TH8_LIMITS = {
    "town_hall": 1,
    "cannon": 5,
    "archer_tower": 5,
    "mortar": 4,
    "air_defense": 3,
    "wizard_tower": 3,
    "bomb_tower": 1,
    "gold_storage": 3,
    "elixir_storage": 3,
    "hidden_tesla": 3,
    "wall": 225,
}


class BaseBuilder:
    """Helper to place buildings and walls on a 44x44 grid without overlaps."""

    def __init__(self, grid_size: int = 44):
        self.grid_size = grid_size
        self.occupied = np.zeros((grid_size, grid_size), dtype=bool)
        self.buildings: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {k: 0 for k in TH8_LIMITS}

    def can_place(self, x: int, y: int, size: int, margin: int = 0) -> bool:
        if x - margin < 1 or y - margin < 1:
            return False
        if x + size + margin > self.grid_size - 1 or y + size + margin > self.grid_size - 1:
            return False
        x0 = max(0, x - margin)
        y0 = max(0, y - margin)
        x1 = min(self.grid_size, x + size + margin)
        y1 = min(self.grid_size, y + size + margin)
        return not self.occupied[y0:y1, x0:x1].any()

    def place_building(self, b_type: str, x: int, y: int) -> bool:
        size = BUILDING_SIZES[b_type]
        if self.counts[b_type] >= TH8_LIMITS[b_type]:
            return False
        if x < 0 or y < 0 or x + size > self.grid_size or y + size > self.grid_size:
            return False
        if self.occupied[y:y + size, x:x + size].any():
            return False
        self.occupied[y:y + size, x:x + size] = True
        self.buildings.append({"type": b_type, "x": int(x), "y": int(y)})
        self.counts[b_type] += 1
        return True

    def place_wall(self, x: int, y: int) -> bool:
        if self.counts["wall"] >= TH8_LIMITS["wall"]:
            return False
        if 0 <= x < self.grid_size and 0 <= y < self.grid_size and not self.occupied[y, x]:
            self.occupied[y, x] = True
            self.buildings.append({"type": "wall", "x": int(x), "y": int(y)})
            self.counts["wall"] += 1
            return True
        return False

    def place_wall_rect(self, x1: int, y1: int, x2: int, y2: int, open_sides: list[str] | None = None) -> int:
        """Place a hollow rectangle of walls from (x1, y1) to (x2, y2)."""
        open_sides = open_sides or []
        placed = 0
        # Horizontal top
        if "top" not in open_sides:
            for x in range(x1, x2 + 1):
                if self.place_wall(x, y1):
                    placed += 1
        # Horizontal bottom
        if "bottom" not in open_sides:
            for x in range(x1, x2 + 1):
                if self.place_wall(x, y2):
                    placed += 1
        # Vertical left
        if "left" not in open_sides:
            for y in range(y1 + 1, y2):
                if self.place_wall(x1, y):
                    placed += 1
        # Vertical right
        if "right" not in open_sides:
            for y in range(y1 + 1, y2):
                if self.place_wall(x2, y):
                    placed += 1
        return placed


def _place_buildings_near(builder: BaseBuilder, rng: random.Random, b_type: str, target_x: int, target_y: int, max_dist: int = 15) -> bool:
    """Find nearest valid spot to (target_x, target_y) for a building."""
    size = BUILDING_SIZES[b_type]
    candidates = []
    for dx in range(-max_dist, max_dist + 1):
        for dy in range(-max_dist, max_dist + 1):
            x = target_x + dx
            y = target_y + dy
            if builder.can_place(x, y, size):
                d = dx * dx + dy * dy
                candidates.append((d, x, y))
    if not candidates:
        return False
    candidates.sort(key=lambda item: item[0])
    # Pick among top candidates with small jitter
    top_n = min(4, len(candidates))
    _, x, y = rng.choice(candidates[:top_n])
    return builder.place_building(b_type, x, y)


def _generate_layout(builder: BaseBuilder, rng: random.Random, style: str):
    """Procedurally place buildings and walls according to style."""
    # Standard TH8 roster: 1 TH, 6 storages, 21 defenses = 31 total buildings
    defense_pool = (
        ["air_defense"] * 3 +
        ["wizard_tower"] * 3 +
        ["bomb_tower"] * 1 +
        ["mortar"] * 4 +
        ["cannon"] * 5 +
        ["archer_tower"] * 5 +
        ["hidden_tesla"] * 3
    )
    storage_pool = ["gold_storage"] * 3 + ["elixir_storage"] * 3

    if style == "compartmented":
        # Concentric rings / 5-compartment layout
        # 1. Town Hall at center
        cx, cy = 20, 20
        builder.place_building("town_hall", cx, cy)

        # 2. Place 2 storages and 1 AD in core compartment
        _place_buildings_near(builder, rng, "gold_storage", cx - 4, cy)
        _place_buildings_near(builder, rng, "elixir_storage", cx + 5, cy)
        _place_buildings_near(builder, rng, "air_defense", cx, cy - 4)

        # Inner wall ring enclosing core
        builder.place_wall_rect(cx - 5, cy - 5, cx + 8, cy + 8)

        # 4 quadrant hubs
        quad_centers = [
            (cx - 8, cy - 8),
            (cx + 11, cy - 8),
            (cx - 8, cy + 11),
            (cx + 11, cy + 11),
        ]
        rng.shuffle(defense_pool)
        rng.shuffle(storage_pool)

        # Distribute remaining storages across quadrants
        for st in storage_pool:
            q = rng.choice(quad_centers)
            _place_buildings_near(builder, rng, st, q[0], q[1])

        # Distribute defenses across quadrants
        for def_b in defense_pool:
            q = rng.choice(quad_centers)
            _place_buildings_near(builder, rng, def_b, q[0], q[1])

        # Compartment walls around quadrants
        builder.place_wall_rect(cx - 13, cy - 13, cx - 1, cy - 1)
        builder.place_wall_rect(cx + 4, cy - 13, cx + 16, cy - 1)
        builder.place_wall_rect(cx - 13, cy + 4, cx - 1, cy + 16)
        builder.place_wall_rect(cx + 4, cy + 4, cx + 16, cy + 16)

    elif style == "clustered_core":
        # Central bunker with Town Hall, storages, and high-DPS splash
        cx, cy = 20, 20
        builder.place_building("town_hall", cx, cy)

        # Storages tightly flanking TH
        for st in storage_pool:
            _place_buildings_near(builder, rng, st, cx, cy, max_dist=7)

        # Wizard towers & Bomb Tower in core
        for wt in ["wizard_tower"] * 3 + ["bomb_tower"]:
            _place_buildings_near(builder, rng, wt, cx, cy, max_dist=8)

        # Heavy core wall ring
        builder.place_wall_rect(cx - 8, cy - 8, cx + 11, cy + 11)

        # Outer defense ring
        outer_angles = np.linspace(0, 2 * math.pi, len(defense_pool) - 4, endpoint=False)
        remaining_defenses = [d for d in defense_pool if d not in ["wizard_tower", "bomb_tower"]]
        rng.shuffle(remaining_defenses)
        radius = 13.0
        for i, b_type in enumerate(remaining_defenses):
            ang = outer_angles[i] + rng.uniform(-0.15, 0.15)
            tx = int(cx + 2 + radius * math.cos(ang))
            ty = int(cy + 2 + radius * math.sin(ang))
            _place_buildings_near(builder, rng, b_type, tx, ty, max_dist=5)

        # Segmented wall teeth between outer defenses
        for ang in outer_angles[::2]:
            wx = int(cx + 2 + (radius + 2.5) * math.cos(ang))
            wy = int(cy + 2 + (radius + 2.5) * math.sin(ang))
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx == 0 or dy == 0:
                        builder.place_wall(wx + dx, wy + dy)

    elif style == "spread_out":
        # Spaced defense islands across the map
        cx, cy = 20, 20
        builder.place_building("town_hall", cx, cy)

        # 8 radial island nodes
        angles = np.linspace(0, 2 * math.pi, 8, endpoint=False)
        nodes = [(int(cx + 2 + 11 * math.cos(a)), int(cy + 2 + 11 * math.sin(a))) for a in angles]
        nodes.append((cx - 5, cy))
        nodes.append((cx + 6, cy))

        all_buildings = storage_pool + defense_pool
        rng.shuffle(all_buildings)
        for b_type in all_buildings:
            node = rng.choice(nodes)
            _place_buildings_near(builder, rng, b_type, node[0], node[1], max_dist=6)

        # Small wall enclosures around 4 of the nodes
        for node in nodes[:4]:
            builder.place_wall_rect(node[0] - 3, node[1] - 3, node[0] + 4, node[1] + 4)
        # Center wall ring around TH
        builder.place_wall_rect(cx - 2, cy - 2, cx + 5, cy + 5)

    elif style == "defenses_outside":
        # Bait / Southern Teaser style: Core storages + TH, all defenses outside
        cx, cy = 20, 20
        builder.place_building("town_hall", cx, cy)

        # Core storages + Teslas
        for st in storage_pool:
            _place_buildings_near(builder, rng, st, cx, cy, max_dist=7)
        for ht in ["hidden_tesla"] * 3:
            _place_buildings_near(builder, rng, ht, cx, cy, max_dist=6)

        # Protective double wall around resource core
        builder.place_wall_rect(cx - 7, cy - 7, cx + 10, cy + 10)

        # Perimeter defenses placed outside walls
        remaining_defenses = [d for d in defense_pool if d != "hidden_tesla"]
        rng.shuffle(remaining_defenses)
        angles = np.linspace(0, 2 * math.pi, len(remaining_defenses), endpoint=False)
        radius = 13.5
        for i, b_type in enumerate(remaining_defenses):
            ang = angles[i] + rng.uniform(-0.1, 0.1)
            tx = int(cx + 2 + radius * math.cos(ang))
            ty = int(cy + 2 + radius * math.sin(ang))
            _place_buildings_near(builder, rng, b_type, tx, ty, max_dist=6)

    elif style == "asymmetric":
        # Offset TH to one quadrant (e.g. South), heavy defense bastion on North
        th_x, th_y = 20, 28
        builder.place_building("town_hall", th_x, th_y)
        builder.place_wall_rect(th_x - 3, th_y - 2, th_x + 6, th_y + 5)

        # North Bastion center
        nb_x, nb_y = 20, 13
        # High value splash / air defenses in North bastion
        core_defenses = ["air_defense"] * 3 + ["wizard_tower"] * 3 + ["bomb_tower"]
        for cd in core_defenses:
            _place_buildings_near(builder, rng, cd, nb_x, nb_y, max_dist=6)
        for st in storage_pool[:3]:
            _place_buildings_near(builder, rng, st, nb_x, nb_y, max_dist=7)

        # North bastion wall
        builder.place_wall_rect(nb_x - 8, nb_y - 6, nb_x + 10, nb_y + 8)

        # Flanking defenses
        flank_defenses = [d for d in defense_pool if d not in core_defenses] + storage_pool[3:]
        rng.shuffle(flank_defenses)
        flank_nodes = [(10, 22), (30, 22), (20, 22)]
        for b_type in flank_defenses:
            node = rng.choice(flank_nodes)
            _place_buildings_near(builder, rng, b_type, node[0], node[1], max_dist=7)

        # Wall funnels linking north and south
        for y in range(nb_y + 9, th_y - 2):
            builder.place_wall(13, y)
            builder.place_wall(27, y)

    elif style == "mixed":
        # West compartmented, East open funnels
        cx, cy = 20, 20
        builder.place_building("town_hall", cx, cy)

        # West: 2 walled compartments
        west_buildings = defense_pool[:9] + storage_pool[:3]
        rng.shuffle(west_buildings)
        for b_type in west_buildings:
            _place_buildings_near(builder, rng, b_type, cx - 8, cy + rng.randint(-6, 6), max_dist=6)

        builder.place_wall_rect(cx - 13, cy - 10, cx - 1, cy - 1)
        builder.place_wall_rect(cx - 13, cy + 1, cx - 1, cy + 10)

        # East: Open defensive array
        east_buildings = defense_pool[9:] + storage_pool[3:]
        rng.shuffle(east_buildings)
        for b_type in east_buildings:
            _place_buildings_near(builder, rng, b_type, cx + 8, cy + rng.randint(-8, 8), max_dist=7)

        # Staggered wall barriers in East
        for y in range(cy - 8, cy + 9, 4):
            for x in range(cx + 3, cx + 14):
                if (x + y) % 3 != 0:
                    builder.place_wall(x, y)

    elif style == "open_no_walls":
        # Clean open layout with 0 walls
        cx, cy = 20, 20
        builder.place_building("town_hall", cx, cy)
        all_buildings = storage_pool + defense_pool
        rng.shuffle(all_buildings)
        angles = np.linspace(0, 2 * math.pi, len(all_buildings), endpoint=False)
        for i, b_type in enumerate(all_buildings):
            rad = rng.uniform(6.0, 14.0)
            ang = angles[i] + rng.uniform(-0.1, 0.1)
            tx = int(cx + 2 + rad * math.cos(ang))
            ty = int(cy + 2 + rad * math.sin(ang))
            _place_buildings_near(builder, rng, b_type, tx, ty, max_dist=6)
        # 0 walls placed!


def generate_base(seed: int, style: str | None = None) -> dict[str, Any]:
    """Generate a valid, deterministic TH8 base JSON dict for a given seed."""
    rng = random.Random(seed)
    chosen_style = style if style is not None else rng.choice(STYLES)
    if chosen_style not in STYLES:
        raise ValueError(f"Unknown style {chosen_style!r}. Must be one of {STYLES}")

    # Generate layout
    builder = BaseBuilder(grid_size=44)
    _generate_layout(builder, rng, chosen_style)

    # Compile result
    result = {
        "_note": f"Procedurally generated TH8 layout (seed={seed}, style={chosen_style}).",
        "grid": 44,
        "style": chosen_style,
        "seed": seed,
        "buildings": builder.buildings,
    }
    return result
