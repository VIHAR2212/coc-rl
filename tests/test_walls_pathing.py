import numpy as np

from sim import CoCEnv
from sim.entities import Building
from sim.pathing import astar_path


def _make_wall_test_env(wall_coords):
    env = CoCEnv(base_file="base01.json", army="mixed_wb")
    env.reset(seed=0)
    env.buildings = [
        Building(kind="town_hall", x=20, y=20, size=4, hp=3900, max_hp=3900, is_town_hall=True),
    ]
    env._wall_grid = np.zeros((env.grid, env.grid), dtype=bool)
    env._wall_version = 0
    env._path_cache = {}
    for wx, wy in wall_coords:
        w = Building(kind="wall", x=wx, y=wy, size=1, hp=3000, max_hp=3000, is_wall=True)
        env.buildings.append(w)
        env._wall_grid[wy, wx] = True
    env._non_walls = [b for b in env.buildings if not b.is_wall]
    env._defenses = [b for b in env.buildings if b.is_defense]
    env._deploy_mask = np.ones((env.grid, env.grid), dtype=np.float32)
    return env


def test_astar_path_exists_around_open_wall():
    grid = np.zeros((44, 44), dtype=bool)
    for y in range(15, 28):
        grid[y, 18] = True
    path = astar_path(grid, (10, 22), 22.0, 22.0, 4, 0.4)
    assert path is not None and len(path) > 0
    assert all(not grid[int(py), int(px)] for px, py in path)


def test_blocked_path_troop_attacks_wall_and_walls_excluded_from_destruction():
    walls = []
    for x in range(18, 26):
        walls.extend([(x, 18), (x, 25)])
    for y in range(19, 25):
        walls.extend([(18, y), (25, y)])
    env = _make_wall_test_env(walls)
    env._spawn("barbarian_l5", 10, 21)
    tr = env.troops[0]
    for _ in range(80):
        env._sim_tick()
    assert tr.target is not None and tr.target.is_wall
    assert tr.target.hp < tr.target.max_hp
    # Break one wall manually and verify destruction % excludes walls
    env.buildings[1].hp = 0
    assert env._destruction_now() == 0.0


def test_wall_breaker_targets_and_damages_walls():
    walls = [(18, y) for y in range(19, 24)]
    env = _make_wall_test_env(walls)
    env._spawn("wall_breaker_l5", 12, 21)
    wb = env.troops[0]
    for _ in range(60):
        env._sim_tick()
        if not wb.alive:
            break
    assert not wb.alive
    damaged = [b for b in env.buildings if b.is_wall and b.hp < b.max_hp]
    assert len(damaged) >= 1
    assert any(b.hp == b.max_hp - 1720 for b in damaged)

