"""Unit tests for M5b expanded troop mechanics:
- Wizard ranged splash
- Valkyrie melee whirlwind splash
- Hog Rider wall-jump & defense targeting
- Golem death splash & split into 2 Golemites
- Flying troop wall immunity & ground defense immunity
- Balloon defense targeting & death bomb
- Dragon flying ranged splash
"""
import math
import numpy as np
import pytest

from sim import CoCEnv
from sim.entities import Building, Troop


def _make_custom_env(buildings, troop_counts=None):
    """Helper to construct an isolated CoCEnv with custom buildings."""
    env = CoCEnv(base_file="base01.json")
    env.tick = 0
    env.buildings = list(buildings)
    env._non_walls = [b for b in env.buildings if not b.is_wall]
    env._defenses = [b for b in env.buildings if b.is_defense]
    env.troops = []
    env.projectiles = []
    env._wall_grid = np.zeros((env.grid, env.grid), dtype=bool)
    env._wall_hp_grid = np.zeros((env.grid, env.grid), dtype=np.float32)
    env._wall_version = 0
    env._path_cache = {}
    for b in env.buildings:
        if b.is_wall:
            env._wall_grid[int(b.y), int(b.x)] = True
            env._wall_hp_grid[int(b.y), int(b.x)] = 1.0
    for b in env._defenses:
        b.cooldown = 0.0
    return env


def test_wizard_ranged_splash():
    """Wizard attacks a building at range; splash damages adjacent buildings within splash_radius."""
    # Place two 2x2 buildings right next to each other
    b1 = Building(kind="storage", x=10, y=10, size=2, hp=500, max_hp=500)
    b2 = Building(kind="storage", x=12, y=10, size=2, hp=500, max_hp=500)
    env = _make_custom_env([b1, b2])

    # Spawn wizard within range (range_tiles=3.0)
    env._spawn("wizard_l5", 10, 7)
    assert len(env.troops) == 1
    wiz = env.troops[0]
    assert wiz.splash_radius == 0.3

    # Run ticks where wizard attacks b1
    for _ in range(10):
        env._sim_tick()

    # Both buildings must have sustained damage due to area splash
    assert b1.hp < 500, "Target building should be damaged"
    assert b2.hp < 500, "Adjacent building within splash radius should also take splash damage"


def test_valkyrie_whirlwind_splash():
    """Valkyrie whirlwind deals 360-degree melee splash damage to all buildings in reach."""
    # Place two buildings separated by 1 tile, valkyrie standing between them
    b1 = Building(kind="storage", x=10, y=10, size=2, hp=600, max_hp=600)
    b2 = Building(kind="storage", x=13, y=10, size=2, hp=600, max_hp=600)
    env = _make_custom_env([b1, b2])

    # Spawn valkyrie at (12, 10) between both buildings
    env._spawn("valkyrie_l2", 12, 10)
    valk = env.troops[0]
    assert valk.whirlwind is True
    assert valk.splash_radius == 1.0

    for _ in range(10):
        env._sim_tick()

    assert b1.hp < 600, "First building should take whirlwind damage"
    assert b2.hp < 600, "Second building should take whirlwind damage"


def test_hog_rider_wall_jump_and_defense_target():
    """Hog Rider jumps directly over walls without breaking them, heading straight for defenses."""
    # Create a line of walls blocking direct path to a cannon
    walls = [Building(kind="wall", x=15, y=y, size=1, hp=3000, max_hp=3000, is_wall=True) for y in range(8, 16)]
    cannon = Building(kind="cannon", x=18, y=11, size=3, hp=960, max_hp=960, is_defense=True, dps=0)  # non-firing
    gold = Building(kind="gold_storage", x=10, y=5, size=3, hp=2000, max_hp=2000)
    env = _make_custom_env(walls + [cannon, gold])

    # Spawn Hog Rider on west side of wall line
    env._spawn("hog_rider_l4", 10, 11)
    hog = env.troops[0]
    assert hog.wall_jumper is True
    assert hog.favorite == "defenses"

    # Hog must pick the Cannon (defense), not gold storage
    env._sim_tick()
    assert hog.target == cannon

    # Advance several ticks; Hog Rider moves straight east (increasing x) crossing wall x=15
    for _ in range(30):
        env._sim_tick()

    # Hog should have crossed x=15 toward x=18
    assert hog.x > 15.0, f"Hog Rider should have jumped walls to x > 15, actual x={hog.x:.2f}"
    # Walls must be undamaged
    for w in walls:
        assert w.hp == 3000, "Hog Rider must jump over walls without damaging them"


def test_golem_death_split_and_splash():
    """Golem targets defenses, has high HP, and on death deals splash damage and splits into 2 Golemites."""
    target_def = Building(kind="cannon", x=12, y=12, size=3, hp=1000, max_hp=1000, is_defense=True)
    env = _make_custom_env([target_def])

    env._spawn("golem_l2", 10, 12)
    golem = env.troops[0]
    assert golem.hp == 5400
    assert golem.splits_into == 2
    assert golem.split_troop == "golemite_l2"
    assert golem.death_damage == 400

    # Let Golem move close to cannon
    for _ in range(15):
        env._sim_tick()

    cannon_hp_before = target_def.hp
    # Kill the Golem
    golem.hp = 0.0

    # Next sim tick should trigger death splash and spawn 2 Golemites
    env._sim_tick()

    # Death damage check (400 splash)
    assert target_def.hp <= cannon_hp_before - 400 + 1e-3, "Cannon must take Golem death explosion splash"

    # Verify 2 Golemites are spawned
    assert len(env.troops) == 2, f"Expected 2 Golemites, got {len(env.troops)}"
    for g_mite in env.troops:
        assert g_mite.name == "Golemite"
        assert g_mite.hp == 1080
        assert g_mite.favorite == "defenses"
        assert g_mite.death_damage == 80


def test_flying_troops_ground_defense_immunity_and_air_defense():
    """Flying troops fly over walls, take zero damage from ground-only defenses, but take damage from Air Defense."""
    cannon = Building(kind="cannon", x=10, y=10, size=3, hp=960, max_hp=960, is_defense=True, dps=100, attack_speed=1.0, range_tiles=9.0, targets="ground")
    mortar = Building(kind="mortar", x=10, y=14, size=3, hp=650, max_hp=650, is_defense=True, dps=50, attack_speed=1.0, range_tiles=11.0, targets="ground", splash_radius=1.5)
    bomb_tower = Building(kind="bomb_tower", x=10, y=18, size=3, hp=700, max_hp=700, is_defense=True, dps=50, attack_speed=1.0, range_tiles=6.0, targets="ground", splash_radius=1.5)
    air_def = Building(kind="air_defense", x=10, y=22, size=3, hp=1050, max_hp=1050, is_defense=True, dps=200, attack_speed=1.0, range_tiles=10.0, targets="air")

    env = _make_custom_env([cannon, mortar, bomb_tower, air_def])

    # 1. Spawn Minion in range of Cannon, Mortar, Bomb Tower, but outside Air Defense range
    env._spawn("minion_l4", 10, 10)
    minion = env.troops[0]
    assert minion.is_flying is True
    initial_hp = minion.hp

    # Tick 5 times: ground defenses must NOT attack minion
    for _ in range(5):
        env._sim_tick()

    assert minion.hp == initial_hp, "Minion should take zero damage from ground-only defenses (Cannon, Mortar, Bomb Tower)"

    # 2. Now spawn Dragon in range of Air Defense
    env._spawn("dragon_l3", 10, 24)
    dragon = env.troops[-1]
    assert dragon.is_flying is True
    d_initial_hp = dragon.hp

    # Tick 15 times: Air defense should target and shoot Dragon
    for _ in range(15):
        env._sim_tick()

    assert dragon.hp < d_initial_hp, "Air defense must target and damage flying Dragon"


def test_balloon_defense_targeting_and_death_bomb():
    """Balloon targets defenses first, flies over walls, and drops death bomb on destruction."""
    wall_ring = [Building(kind="wall", x=15, y=y, size=1, hp=3000, max_hp=3000, is_wall=True) for y in range(8, 16)]
    cannon = Building(kind="cannon", x=18, y=11, size=3, hp=500, max_hp=500, is_defense=True)
    elixir = Building(kind="elixir_storage", x=12, y=5, size=3, hp=2000, max_hp=2000)

    env = _make_custom_env(wall_ring + [cannon, elixir])

    env._spawn("balloon_l5", 10, 11)
    loon = env.troops[0]
    assert loon.is_flying is True
    assert loon.favorite == "defenses"
    assert loon.death_damage == 108

    env._sim_tick()
    assert loon.target == cannon, "Balloon must prioritize defense over storage"

    # Move balloon over the wall until it reaches the cannon
    for _ in range(70):
        env._sim_tick()

    assert loon.x > 15.0, "Balloon must fly directly over walls"
    cannon_hp_before = cannon.hp

    # Kill Balloon right at the cannon
    loon.hp = 0.0
    env._sim_tick()

    # Death bomb damage
    assert cannon.hp <= cannon_hp_before - 108 + 1e-3, "Cannon must take death bomb damage from falling Balloon"


def test_dragon_flying_ranged_splash():
    """Dragon flies over walls and deals area splash damage with ranged breath attacks."""
    b1 = Building(kind="storage", x=15, y=15, size=3, hp=1000, max_hp=1000)
    b2 = Building(kind="storage", x=18, y=15, size=3, hp=1000, max_hp=1000)
    env = _make_custom_env([b1, b2])

    env._spawn("dragon_l3", 11, 15)
    dragon = env.troops[0]
    assert dragon.is_flying is True
    assert dragon.splash_radius == 0.3
    assert dragon.range_tiles == 3.0

    for _ in range(25):
        env._sim_tick()

    assert b1.hp < 1000, "Target building should take Dragon breath damage"
    assert b2.hp < 1000, "Adjacent building within splash radius should take Dragon splash damage"
