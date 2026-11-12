"""Unit tests for M6 baseline strategies and evaluation runner."""
import csv

from agents import STRATEGIES
from evaluate import BASES_DIR, run_baselines
from sim import CoCEnv


def test_at_least_three_distinct_strategies():
    assert len(STRATEGIES) >= 3
    env = CoCEnv(base_file="base04.json", army="mixed_wb")
    actions = set()
    for name, fn in STRATEGIES.items():
        env.reset(seed=7)
        a0 = tuple(fn(env, 0))
        assert env.action_space.contains(list(a0)), f"{name} returned invalid action {a0}"
        actions.add(a0)
    assert len(actions) >= 2


def test_evaluate_writes_baselines_csv(tmp_path, monkeypatch):
    # Restrict bases to one small layout for fast test verification.
    monkeypatch.setattr("evaluate._army_names", lambda: ["barch"])
    out_csv = tmp_path / "baselines.csv"
    rows, best = run_baselines(episodes=2, output_csv=out_csv, workers=1)
    assert out_csv.exists()
    assert best in STRATEGIES
    expected = len(list(BASES_DIR.glob("*.json"))) * 1 * len(STRATEGIES) * 2
    assert len(rows) == expected
    with out_csv.open("r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == expected
    assert {"strategy", "base", "army", "episode", "seed", "destruction", "stars", "three_star"} <= set(reader[0].keys())

