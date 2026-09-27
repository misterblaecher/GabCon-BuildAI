from pathlib import Path

from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.voxel import VoxelGrid


def test_central_portal_blueprint_executes():
    source = Path("blueprints/01-central-portal.py").read_text(encoding="utf-8")
    grid = VoxelGrid()

    run_blueprint(source, grid, seed=0)

    assert len(grid) > 1_000
    assert grid.bounds is not None

    (minx, miny, minz), (maxx, maxy, maxz) = grid.bounds
    dims = (maxx - minx + 1, maxy - miny + 1, maxz - minz + 1)

    assert dims[0] >= 80
    assert dims[1] >= 70
    assert dims[2] >= 50
