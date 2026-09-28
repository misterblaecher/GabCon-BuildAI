"""Reader for vanilla Minecraft structure block `.nbt` files."""

from __future__ import annotations

from pathlib import Path

import nbtlib

from mcbuild.dataset.models import CanonicalStructure
from mcbuild.dataset.normalize import normalize_structure


def _palette_state(entry) -> str:
    name = str(entry["Name"])
    props = entry.get("Properties")
    if not props:
        return name
    body = ",".join(f"{key}={props[key]}" for key in sorted(props))
    return f"{name}[{body}]"


class MinecraftStructureReader:
    def can_read(self, path: Path) -> bool:
        return path.suffix.lower() == ".nbt"

    def read(self, path: Path) -> CanonicalStructure:
        root = nbtlib.load(str(path))
        if "size" not in root or "palette" not in root or "blocks" not in root:
            raise ValueError("NBT file is not a vanilla Minecraft structure block export.")
        dimensions = tuple(int(value) for value in root["size"])
        if len(dimensions) != 3:
            raise ValueError("Minecraft structure size must contain exactly three axes.")
        palette = [_palette_state(entry) for entry in root["palette"]]
        rows: list[tuple[int, int, int, str]] = []
        for entry in root["blocks"]:
            x, y, z = (int(value) for value in entry["pos"])
            state_index = int(entry["state"])
            try:
                state = palette[state_index]
            except IndexError as exc:
                raise ValueError(f"Invalid Minecraft structure palette index {state_index}.") from exc
            rows.append((x, y, z, state))
        return normalize_structure(
            rows,
            dimensions=dimensions,  # type: ignore[arg-type]
            metadata={"format": "minecraft_structure_nbt", "data_version": int(root.get("DataVersion", 0)) or None},
        )
