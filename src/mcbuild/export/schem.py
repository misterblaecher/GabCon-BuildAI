"""Sponge Schematic v3 export (WorldEdit-compatible .schem), via nbtlib.

WorldEdit 7.3+ loads modern .schem files via SpongeSchematicV3Reader, which expects
an unnamed root compound containing a child "Schematic" tag, with block data nested
under "Blocks" (not the flat v2 layout). See:
https://github.com/EngineHub/WorldEdit/blob/master/worldedit-core/src/main/java/com/sk89q/worldedit/extent/clipboard/io/sponge/SpongeSchematicV3Reader.java

DataVersion 3955 corresponds to Minecraft 1.21.1.
"""

from __future__ import annotations

import nbtlib
import numpy as np
from nbtlib.tag import ByteArray, Compound, Int, IntArray, List, Short

from mcbuild.palette import get_block_by_index
from mcbuild.validation import validate_structural_blocks
from mcbuild.voxel import VoxelGrid

DATA_VERSION = 3955


def _varint(value: int) -> list[int]:
    out = []
    v = value
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return out


def _encode_block_data(dense: np.ndarray, palette_size: int) -> ByteArray:
    """Encode the Sponge v3 varint stream without Python lists per voxel.

    The common case (up to 128 palette entries) uses one byte per block and
    NumPy vectorization. Larger palettes use one cached varint encoding per
    distinct palette entry rather than encoding every cell independently.
    """
    if palette_size <= 128:
        return ByteArray(dense.astype(np.int8, copy=False))

    varints = tuple(bytes(_varint(index)) for index in range(palette_size))
    encoded = bytearray()
    extend = encoded.extend
    for index in dense:
        extend(varints[int(index)])
    return ByteArray(np.frombuffer(encoded, dtype=np.int8))


def grid_to_schematic(grid: VoxelGrid, *, validate: bool = True) -> Compound:
    """Build Sponge v3 NBT. Skip validation only if the caller already validated."""
    if validate:
        validate_structural_blocks(grid)
    bounds = grid.bounds
    if bounds is None:
        raise ValueError("Cannot export an empty voxel grid.")
    (minx, miny, minz), (maxx, maxy, maxz) = bounds
    width = maxx - minx + 1
    height = maxy - miny + 1
    length = maxz - minz + 1

    used_indices = sorted({idx for _, idx in grid.items()})
    palette_compound = Compound()
    mc_id_to_palette_id: dict[int, int] = {}
    for palette_id, idx in enumerate(used_indices):
        block = get_block_by_index(idx)
        mc_id_to_palette_id[idx] = palette_id
        palette_compound[block.mc_id] = Int(palette_id)

    # Unused volume is filled with air. If the build already places explicit "air"
    # cells, reuse that palette entry rather than adding a duplicate (a duplicate
    # would collide in the name-keyed Palette compound and corrupt the mapping).
    if "minecraft:air" in palette_compound:
        air_palette_id = int(palette_compound["minecraft:air"])
    else:
        air_palette_id = len(palette_compound)
        palette_compound["minecraft:air"] = Int(air_palette_id)

    volume = width * height * length
    dtype = np.uint8 if len(palette_compound) <= 256 else (np.uint16 if len(palette_compound) <= 65536 else np.uint32)
    dense = np.full(volume, air_palette_id, dtype=dtype)
    for (x, y, z), idx in grid.items():
        lx, ly, lz = x - minx, y - miny, z - minz
        pos = lx + lz * width + ly * width * length
        dense[pos] = mc_id_to_palette_id[idx]

    block_data = _encode_block_data(dense, len(palette_compound))

    schematic = Compound(
        {
            "Version": Int(3),
            "DataVersion": Int(DATA_VERSION),
            "Width": Short(width),
            "Height": Short(height),
            "Length": Short(length),
            "Offset": IntArray([minx, miny, minz]),
            "Blocks": Compound(
                {
                    "Palette": palette_compound,
                    "Data": block_data,
                    "BlockEntities": List[Compound]([]),
                }
            ),
            "Entities": List[Compound]([]),
        }
    )
    return Compound({"Schematic": schematic})


def export_schem(grid: VoxelGrid, path: str, *, validate: bool = True) -> None:
    """Write a gzipped Sponge Schematic v3. Validate unless already checked."""
    root = grid_to_schematic(grid, validate=validate)
    nbt_file = nbtlib.File(root, gzipped=True, root_name="")
    nbt_file.save(path)
