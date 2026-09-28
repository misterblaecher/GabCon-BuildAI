"""Reader for Hack337-style JSON blueprint grids."""

from __future__ import annotations

import json
from pathlib import Path

from mcbuild.dataset.models import CanonicalStructure
from mcbuild.dataset.normalize import normalize_structure


class BlueprintJsonReader:
    def can_read(self, path: Path) -> bool:
        return path.suffix.lower() == ".json" and "blueprint" in path.name.lower()

    def read(self, path: Path) -> CanonicalStructure:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not {"size", "palette", "layers"}.issubset(raw):
            raise ValueError("Not a supported Minecraft blueprint JSON object.")
        width, height, depth = (int(value) for value in raw["size"])
        palette = {str(key): str(value) for key, value in raw["palette"].items()}
        rows: list[tuple[int, int, int, str]] = []
        layers = raw["layers"]
        if len(layers) != height:
            raise ValueError("Blueprint layer count does not match declared height.")
        for y, layer in enumerate(layers):
            if len(layer) != depth:
                raise ValueError(f"Blueprint layer {y} does not match declared depth.")
            for z, row in enumerate(layer):
                if len(row) != width:
                    raise ValueError(f"Blueprint row y={y} z={z} does not match declared width.")
                for x, token in enumerate(row):
                    if token == ".":
                        continue
                    state = palette.get(token)
                    if state is None:
                        raise ValueError(f"Blueprint token {token!r} is missing from its palette.")
                    rows.append((x, y, z, state))
        return normalize_structure(
            rows,
            dimensions=(width, height, depth),
            metadata={"format": "blueprint_json"},
        )
