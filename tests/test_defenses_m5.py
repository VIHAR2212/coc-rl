"""Unit tests for M5 defense realism mechanics."""
import pytest

from sim.entities import Building, Troop
from sim.env import CoCEnv


def _bare_env() -> CoCEnv:
    env = CoCEnv(base_file="base01.json", army="barch")
    env.reset(seed=0)
    env.troops = []
    env.projectiles = []
    th = next(b for b in env.buildings if b.is_town_hall)
    th.x, th.y = 0.0, 0.0
    env.buildings = [th]
    env._non_walls = [th]
    env._defenses = []
    return env


def _add_defense(env: CoCEnv, kind: str, x: float, y: float, projectile_delay: float = 0.0) -> Building:
    d = env.defense_defs[kind]
    bld = Building(
        kind=kind,
        x=x,
        y=y,
        size=d["size"],
        hp=d["hp"],
        max_hp=d["hp"],
        dps=d["dps"],
        range_tiles=d["range_tiles"],
        attack_speed=d["attack_speed"],
        min_range_tiles=d.get("min_range_tiles", 0.0),
        splash_radius=d.get("splash_radius", 0.0),
        targets=d["targets"],
        projectile_delay=projectile_delay,
        is_defense=True,
    )
    env.buildings.append(bld)
    env._non_walls.append(bld)
    env._defenses.append(bld)
    return bld


def _dummy_troop(x: float, y: float, hp: float = 500.0, is_flying: bool = False) -> Troop:
    return Troop(
        name="Dummy",
        x=x,
        y=y,
        hp=hp,
        dps=0.0,
        attack_speed=1.0,
        range_tiles=1.0,
        speed=0.0,
        favorite="any",
        housing=1,
        is_flying=is_flying,
    )


def test_mortar_min_range():
    env = _bare_env()
    mortar = _add_defense(env, "mortar", 20.0, 20.0)  # center = (21.5, 21.5)
    inside_blind = _dummy_troop(mortar.cx + 2.5, mortar.cy, hp=500.0)
    in_band = _dummy_troop(mortar.cx + 6.0, mortar.cy, hp=500.0)
    env.troops = [inside_blind, in_band]

    env._sim_tick()

    assert inside_blind.hp == pytest.approx(500.0)
    expected_shot = mortar.dps * mortar.attack_speed
    assert in_band.hp == pytest.approx(500.0 - expected_shot)


def test_mortar_splash():
    env = _bare_env()
    mortar = _add_defense(env, "mortar", 20.0, 20.0)  # splash_radius = 1.5
    primary = _dummy_troop(mortar.cx + 6.0, mortar.cy, hp=500.0)
    nearby = _dummy_troop(mortar.cx + 7.2, mortar.cy, hp=500.0)   # dist from primary = 1.2 <= 1.5
    outside = _dummy_troop(mortar.cx + 8.0, mortar.cy, hp=500.0)  # dist from primary = 2.0 > 1.5
    env.troops = [primary, nearby, outside]

    env._sim_tick()

    shot = mortar.dps * mortar.attack_speed
    assert primary.hp == pytest.approx(500.0 - shot)
    assert nearby.hp == pytest.approx(500.0 - shot)
    assert outside.hp == pytest.approx(500.0)


def test_wizard_tower_splash():
    env = _bare_env()
    wt = _add_defense(env, "wizard_tower", 20.0, 20.0)  # splash_radius = 1.0, targets = air_ground
    g1 = _dummy_troop(wt.cx + 3.0, wt.cy, hp=500.0, is_flying=False)
    a2 = _dummy_troop(wt.cx + 3.8, wt.cy, hp=500.0, is_flying=True)   # dist = 0.8 <= 1.0
    far = _dummy_troop(wt.cx + 4.5, wt.cy, hp=500.0, is_flying=False)  # dist = 1.5 > 1.0
    env.troops = [g1, a2, far]

    env._sim_tick()

    shot = wt.dps * wt.attack_speed
    assert g1.hp == pytest.approx(500.0 - shot)
    assert a2.hp == pytest.approx(500.0 - shot)
    assert far.hp == pytest.approx(500.0)


def test_air_defense_air_only():
    env = _bare_env()
    ad = _add_defense(env, "air_defense", 20.0, 20.0)  # targets = air
    ground = _dummy_troop(ad.cx + 3.0, ad.cy, hp=500.0, is_flying=False)
    air = _dummy_troop(ad.cx + 5.0, ad.cy, hp=500.0, is_flying=True)
    env.troops = [ground, air]

    env._sim_tick()

    assert ground.hp == pytest.approx(500.0)
    assert air.hp == pytest.approx(500.0 - ad.dps * ad.attack_speed)


def test_attack_speed_and_projectile_delay():
    # Discrete attack-speed cadence on Cannon (attack_speed = 0.8s = 8 ticks)
    env = _bare_env()
    cannon = _add_defense(env, "cannon", 20.0, 20.0, projectile_delay=0.0)
    tr = _dummy_troop(cannon.cx + 3.0, cannon.cy, hp=500.0)
    env.troops = [tr]

    shot = cannon.dps * cannon.attack_speed
    env._sim_tick()  # t=0.0s -> fires 1st shot
    assert tr.hp == pytest.approx(500.0 - shot)
    for _ in range(7):  # t=0.1..0.7s -> on cooldown, no damage
        env._sim_tick()
    assert tr.hp == pytest.approx(500.0 - shot)
    env._sim_tick()  # t=0.8s -> fires 2nd shot
    assert tr.hp == pytest.approx(500.0 - 2 * shot)

    # Non-zero projectile delay defers damage cleanly
    env2 = _bare_env()
    delayed = _add_defense(env2, "cannon", 20.0, 20.0, projectile_delay=0.5)
    tr2 = _dummy_troop(delayed.cx + 3.0, delayed.cy, hp=500.0)
    env2.troops = [tr2]

    env2._sim_tick()  # fires at t=0.0s, lands at t=0.5s
    assert tr2.hp == pytest.approx(500.0)
    for _ in range(4):  # t=0.1..0.4s -> still in flight
        env2._sim_tick()
        assert tr2.hp == pytest.approx(500.0)
    env2._sim_tick()  # t=0.5s -> impact resolves
    assert tr2.hp == pytest.approx(500.0 - shot)

