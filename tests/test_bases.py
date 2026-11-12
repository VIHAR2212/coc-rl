from pathlib import Path

from scripts.validate_base import BASES_DIR, validate_base
from sim import CoCEnv


def test_all_bases_valid():
    base_files = sorted(BASES_DIR.glob("*.json"))
    assert len(base_files) >= 6
    for path in base_files:
        errors = validate_base(path)
        assert errors == [], f"{path.name} failed validation: {errors}"


def test_all_bases_load_in_env():
    for path in sorted(BASES_DIR.glob("*.json")):
        env = CoCEnv(base_file=path.name)
        obs, _ = env.reset(seed=0)
        assert obs["grid"].shape == (5, 44, 44)

