from pathlib import Path

import pytest

from mcbuild import palette
from mcbuild.dsl.sandbox import compile_blueprint, run_blueprint
from mcbuild.profile import resolve_registry_path
from mcbuild.voxel import VoxelGrid

MODULE_BLUEPRINTS = [
    Path("blueprints/01-central-portal.py"),
    Path("blueprints/02-cliffside-factory.py"),
    Path("blueprints/03-waterfront-city.py"),
    Path("blueprints/04-observatory.py"),
    Path("blueprints/05-arcane-complex.py"),
    Path("blueprints/06-railway-viaduct.py"),
    Path("blueprints/07-mountain-castle.py"),
]


@pytest.mark.parametrize("path", MODULE_BLUEPRINTS)
def test_module_blueprint_compiles(path: Path):
    compile_blueprint(path.read_text(encoding="utf-8"))


def test_central_portal_blueprint_executes_against_server_registry():
    registry = resolve_registry_path()
    if registry is None:
        pytest.skip("MCBUILD_SERVER_REGISTRY is not configured in this environment")

    palette.configure_server_registry(registry)
    try:
        grid = VoxelGrid()
        source = Path("blueprints/01-central-portal.py").read_text(encoding="utf-8")
        run_blueprint(source, grid, seed=0)
    finally:
        palette.configure_server_profile(None)

    assert len(grid) > 1_000
    assert grid.bounds is not None

    (minx, miny, minz), (maxx, maxy, maxz) = grid.bounds
    dims = (maxx - minx + 1, maxy - miny + 1, maxz - minz + 1)

    assert dims[0] >= 85
    assert dims[1] >= 85
    assert dims[2] >= 55
