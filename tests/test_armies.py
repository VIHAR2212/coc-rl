import json
import pytest

from sim import CoCEnv
from sim.env import ARMY_LIMIT, DATA


def test_armies_fill_th8_capacity_exactly():
    troops = {k: v for k, v in json.loads((DATA / "troops.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}
    armies_raw = json.loads((DATA / "armies.json").read_text(encoding="utf-8"))
    assert ARMY_LIMIT == 200
    assert armies_raw["_housing_capacity"] == ARMY_LIMIT
    armies = {k: v for k, v in armies_raw.items() if not k.startswith("_")}
    assert 3 <= len(armies) <= 10
    for name, comp in armies.items():
        used = sum(count * troops[k]["housing"] for k, count in comp.items())
        assert used == ARMY_LIMIT, f"{name} uses {used} != {ARMY_LIMIT}"


def test_env_accepts_army_name_and_rejects_over_limit():
    env = CoCEnv(army="barch")
    assert env.army_template["barbarian_l5"] == 100
    assert env.army_template["archer_l5"] == 100

    with pytest.raises(ValueError, match="exceeds limit"):
        CoCEnv(army={"giant_l5": 41})  # 205 > 200

