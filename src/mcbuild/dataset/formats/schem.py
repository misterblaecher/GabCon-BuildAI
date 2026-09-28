"""Sponge Schematic v2/v3 reader."""

from __future__ import annotations

from pathlib import Path

import nbtlib

from mcbuild.dataset.models import CanonicalStructure
from mcbuild.dataset.normalize import normalize_structure


def _byte_values(tag) -> bytes:
    return bytes(int(value) & 0xFF for value in tag)


def _decode_varints(raw: bytes, expected: int) -> list[int]:
    values: list[int] = []
    index = 0
    while index < len(raw) and len(values) < expected:
        result = 0
        shift = 0
        while True:
            if index >= len(raw):
                raise ValueError("Truncated Sponge BlockData varint stream.")
            value = raw[index]
            index += 1
            result |= (value & 0x7F) << shift
            if not value & 0x80:
                break
            shift += 7
            if shift > 35:
                raise ValueError("Invalid Sponge BlockData varint.")
        values.append(result)
    if len(values) != expected:
        raise ValueError(f"Expected {expected} block palette indices, decoded {len(values)}.")
    return values


class SpongeSchemReader:
    def can_read(self, path: Path) -> bool:
        return path.suffix.lower() == ".schem"

    def read(self, path: Path) -> CanonicalStructure:
        root = nbtlib.load(str(path))
        schematic = root.get("Schematic", root)
        version = int(schematic.get("Version", 0))
        width = int(schematic["Width"])
        height = int(schematic["Height"])
        length = int(schematic["Length"])
        dimensions = (width, height, length)
        volume = width * height * length
        if volume <= 0:
            raise ValueError(f"Invalid Sponge schematic dimensions: {dimensions!r}")

        if "Blocks" in schematic:
            blocks_tag = schematic["Blocks"]
            palette_tag = blocks_tag["Palette"]
            data_tag = blocks_tag["Data"]
        else:
            palette_tag = schematic["Palette"]
            data_tag = schematic["BlockData"]

        palette = {int(value): str(name) for name, value in palette_tag.items()}
        values = _decode_varints(_byte_values(data_tag), volume)
        rows: list[tuple[int, int, int, str]] = []
        for flat_index, palette_id in enumerate(values):
            state = palette.get(palette_id)
            if state is None:
                raise ValueError(f"Palette index {palette_id} missing from Sponge palette.")
            x = flat_index % width
            z = (flat_index // width) % length
            y = flat_index // (width * length)
            rows.append((x, y, z, state))

        data_version = schematic.get("DataVersion")
        metadata = {
            "format": "sponge_schem",
            "schematic_version": version or None,
            "data_version": int(data_version) if data_version is not None else None,
        }
        return normalize_structure(rows, dimensions=dimensions, metadata=metadata)
