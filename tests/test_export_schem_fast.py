"""Fast varint and validation regression tests for Sponge schematics."""

import nbtlib
import numpy as np

from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import _encode_block_data, export_schem, grid_to_schematic
from mcbuild.voxel import VoxelGrid


def test_fast_byte_palette_encoding():
    indices = np.array([0, 1, 2, 127, 0, 126], dtype=np.uint16)
    encoded = _encode_block_data(indices, 128)
    assert np.asarray(encoded, dtype=np.uint8).tobytes() == bytes([0, 1, 2, 127, 0, 126])


def test_varint_palette_encoding_beyond_128_entries():
    indices = np.array([0, 1, 127, 128, 255, 16384], dtype=np.uint16)
    encoded = _encode_block_data(indices, 16385)
    assert np.asarray(encoded, dtype=np.uint8).tobytes() == b"\x00\x01\x7f\x80\x01\xff\x01\x80\x80\x01"


def test_prevalidated_export_preserves_output(tmp_path):
    grid = VoxelGrid()
    run_blueprint(
        "fill(-3, 0, -2, 4, 3, 2, 'stone_bricks')\nset_block(1, 1, 0, 'air')\nset_block(2, 4, 1, 'glass')",
        grid,
    )
    checked = tmp_path / "checked.schem"
    prevalidated = tmp_path / "prevalidated.schem"
    export_schem(grid, str(checked))
    export_schem(grid, str(prevalidated), validate=False)
    # gzip headers may vary; parsed NBT content must be identical.
    assert nbtlib.load(str(checked)) == nbtlib.load(str(prevalidated))
    assert grid_to_schematic(grid, validate=False) == grid_to_schematic(grid)
