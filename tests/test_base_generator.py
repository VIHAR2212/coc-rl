"""Unit tests for procedural TH8 base generator (Milestone M10)."""

import json
from pathlib import Path

import pytest

from scripts.validate_base import validate_base, _load_defs, _load_th8_limits
from sim.base_generator import generate_base, STYLES, TH8_LIMITS, BUILDING_SIZES


def test_generator_determinism():
    """Generating with the same seed must produce identical base configurations."""
    base1 = generate_base(seed=123, style="compartmented")
    base2 = generate_base(seed=123, style="compartmented")
    assert base1 == base2, "Identical seeds must produce identical base JSONs"

    base_diff = generate_base(seed=124, style="compartmented")
    assert base1["buildings"] != base_diff["buildings"], "Different seeds must produce different layouts"


def test_generator_styles_validity(tmp_path):
    """Every supported style must pass validate_base with zero errors."""
    defs = _load_defs()
    limits = _load_th8_limits()

    for seed, style in enumerate(STYLES):
        base = generate_base(seed=seed, style=style)
        assert base["style"] == style
        assert base["grid"] == 44

        p = tmp_path / f"test_base_{style}.json"
        p.write_text(json.dumps(base), encoding="utf-8")
        errs = validate_base(p, defs=defs, limits=limits)
        assert len(errs) == 0, f"Style {style} failed validation: {errs}"


def test_generator_th8_limits():
    """Generated bases must strictly respect TH8 limits."""
    for seed in range(20):
        base = generate_base(seed=seed)
        counts = {}
        for b in base["buildings"]:
            counts[b["type"]] = counts.get(b["type"], 0) + 1

        assert counts.get("town_hall", 0) == 1, "Must contain exactly 1 Town Hall"
        assert counts.get("wall", 0) <= TH8_LIMITS["wall"], "Wall limit exceeded"
        for kind, limit in TH8_LIMITS.items():
            assert counts.get(kind, 0) <= limit, f"{kind} count {counts.get(kind, 0)} exceeds TH8 limit {limit}"

        combined_storages = counts.get("gold_storage", 0) + counts.get("elixir_storage", 0)
        assert combined_storages <= 6, f"Combined storages {combined_storages} exceed 6"


def test_generator_no_overlap_and_in_bounds():
    """All buildings and walls must stay strictly inside 44x44 grid without overlapping."""
    for seed in range(15):
        base = generate_base(seed=100 + seed)
        placed = []
        for idx, b in enumerate(base["buildings"]):
            kind = b["type"]
            size = BUILDING_SIZES[kind]
            x, y = b["x"], b["y"]

            assert 0 <= x and x + size <= 44, f"Building {kind} at ({x}, {y}) out of x-bounds"
            assert 0 <= y and y + size <= 44, f"Building {kind} at ({x}, {y}) out of y-bounds"

            for p_idx, p_kind, px, py, psize in placed:
                overlap = not (x + size <= px or px + psize <= x or y + size <= py or py + psize <= y)
                assert not overlap, f"Overlap between building[{idx}] {kind}@({x},{y}) and building[{p_idx}] {p_kind}@({px},{py})"

            placed.append((idx, kind, x, y, size))
