"""Ensure the Studio's local organic sample is runnable by the real BuildAI DSL."""

from __future__ import annotations

import ast
from pathlib import Path

from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.voxel import VoxelGrid


def test_studio_organic_tree_example_executes() -> None:
    javascript = (Path(__file__).resolve().parents[1] / "gabcon-studio/static/app.js").read_text(
        encoding="utf-8"
    )
    part = javascript.split("const SAMPLE_ORGANIC = [", 1)[1].split("].join('\\n');", 1)[0]
    source = "\n".join(
        ast.literal_eval(line.strip().rstrip(","))
        for line in part.splitlines()
        if line.strip()
    )

    assert "sphere(" in source and "cylinder(" in source
    assert "spruce_log" in source and "oak_leaves" in source

    grid = VoxelGrid()
    run_blueprint(source, grid, seed=42, max_seconds=20)
    assert len(grid) > 1000
    assert grid.bounds is not None
    low, high = grid.bounds
    assert high[1] - low[1] >= 25
    assert high[0] - low[0] >= 20
    assert high[2] - low[2] >= 20
