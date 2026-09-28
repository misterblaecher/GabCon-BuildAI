"""Minimal Litematica `.litematic` reader using nbtlib only."""

from __future__ import annotations

import math
from pathlib import Path

import nbtlib

from mcbuild.dataset.models import CanonicalStructure
from mcbuild.dataset.normalize import normalize_structure


def _state_string(entry) -> str:
    name = str(entry["Name"])
    properties = entry.get("Properties")
    if not properties:
        return name
    body = ",".join(f"{key}={properties[key]}" for key in sorted(properties))
    return f"{name}[{body}]"


def _unpack_palette_indices(values, count: int, palette_size: int) -> list[int]:
    bits = max(2, math.ceil(math.log2(max(1, palette_size))))
    mask = (1 << bits) - 1
    longs = [int(value) & ((1 << 64) - 1) for value in values]
    out: list[int] = []
    for index in range(count):
        bit_index = index * bits
        long_index = bit_index // 64
        start = bit_index % 64
        if long_index >= len(longs):
            raise ValueError("Truncated Litematica BlockStates array.")
        value = longs[long_index] >> start
        spill = start + bits - 64
        if spill > 0:
            if long_index + 1 >= len(longs):
                raise ValueError("Truncated Litematica BlockStates spill value.")
            value |= longs[long_index + 1] << (bits - spill)
        out.append(value & mask)
    return out


class LitematicReader:
    def can_read(self, path: Path) -> bool:
        return path.suffix.lower() == ".litematic"

    def read(self, path: Path) -> CanonicalStructure:
        root = nbtlib.load(str(path))
        regions = root.get("Regions")
        if not regions:
            raise ValueError("Litematic contains no regions.")

        rows: list[tuple[int, int, int, str]] = []
        bounds: list[tuple[int, int, int, int, int, int]] = []
        for region in regions.values():
            position = region["Position"]
            size = region["Size"]
            px, py, pz = (int(position[axis]) for axis in ("x", "y", "z"))
            sx, sy, sz = (int(size[axis]) for axis in ("x", "y", "z"))
            width, height, length = abs(sx), abs(sy), abs(sz)
            if not width or not height or not length:
                continue
            sign_x = 1 if sx >= 0 else -1
            sign_y = 1 if sy >= 0 else -1
            sign_z = 1 if sz >= 0 else -1
            end_x = px + (width - 1) * sign_x
            end_y = py + (height - 1) * sign_y
            end_z = pz + (length - 1) * sign_z
            bounds.append(
                (
                    min(px, end_x),
                    min(py, end_y),
                    min(pz, end_z),
                    max(px, end_x),
                    max(py, end_y),
                    max(pz, end_z),
                )
            )
            palette = [_state_string(entry) for entry in region["BlockStatePalette"]]
            indices = _unpack_palette_indices(region["BlockStates"], width * height * length, len(palette))
            for flat_index, palette_index in enumerate(indices):
                if palette_index >= len(palette):
                    raise ValueError(f"Invalid Litematica palette index {palette_index}.")
                lx = flat_index % width
                lz = (flat_index // width) % length
                ly = flat_index // (width * length)
                rows.append((px + lx * sign_x, py + ly * sign_y, pz + lz * sign_z, palette[palette_index]))

        metadata_tag = root.get("Metadata", {})
        if not bounds:
            raise ValueError("Litematic contains no non-empty regions.")
        minx = min(bound[0] for bound in bounds)
        miny = min(bound[1] for bound in bounds)
        minz = min(bound[2] for bound in bounds)
        maxx = max(bound[3] for bound in bounds)
        maxy = max(bound[4] for bound in bounds)
        maxz = max(bound[5] for bound in bounds)
        dimensions = (maxx - minx + 1, maxy - miny + 1, maxz - minz + 1)
        metadata = {
            "format": "litematic",
            "minecraft_data_version": int(root.get("MinecraftDataVersion", 0)) or None,
            "name": str(metadata_tag.get("Name", "")) or None,
            "description": str(metadata_tag.get("Description", "")) or None,
        }
        return normalize_structure(rows, dimensions=dimensions, metadata=metadata)
