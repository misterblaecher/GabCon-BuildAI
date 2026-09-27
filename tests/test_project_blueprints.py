from pathlib import Path

import pytest

from mcbuild import palette
from mcbuild.dsl.sandbox import compile_blueprint, run_blueprint
from mcbuild.profile import resolve_registry_path
from mcbuild.voxel import VoxelGrid


def _portal_source() -> str:
    return Path("blueprints/01-central-portal.py").read_text(encoding="utf-8")


def test_central_portal_blueprint_compiles():
    # The portal intentionally uses GabCon server mod blocks, so CI without the
    # exported server registry can still validate the sandbox/Python syntax.
    compile_blueprint(_portal_source())


def test_central_portal_blueprint_executes_against_server_registry():
    registry = resolve_registry_path()
    if registry is None:
        pytest.skip("MCBUILD_SERVER_REGISTRY is not configured in this environment")

    palette.configure_server_registry(registry)
    try:
        grid = VoxelGrid()
        run_blueprint(_portal_source(), grid, seed=0)
    finally:
        palette.configure_server_profile(None)

    assert len(grid) > 1_000
    assert grid.bounds is not None

    (minx, miny, minz), (maxx, maxy, maxz) = grid.bounds
    dims = (maxx - minx + 1, maxy - miny + 1, maxz - minz + 1)

    assert dims[0] >= 85
    assert dims[1] >= 85
    assert dims[2] >= 55
