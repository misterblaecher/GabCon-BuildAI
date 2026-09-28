"""Deterministic structure hashes, including Y-rotation invariant deduplication."""

from __future__ import annotations

import hashlib
import re

from mcbuild.dataset.models import CanonicalBlock, CanonicalStructure, StructureHashes
from mcbuild.dataset.normalize import canonical_block_state

_CARDINAL = ("north", "east", "south", "west")
_CARDINAL_SET = set(_CARDINAL)
_DIRECTION_TOKEN = re.compile(r"(?<![a-z])(north|east|south|west)(?![a-z])")
_RAIL_SHAPES = {
    "north_south": ("north_south", "east_west", "north_south", "east_west"),
    "east_west": ("east_west", "north_south", "east_west", "north_south"),
    "ascending_north": ("ascending_north", "ascending_east", "ascending_south", "ascending_west"),
    "ascending_east": ("ascending_east", "ascending_south", "ascending_west", "ascending_north"),
    "ascending_south": ("ascending_south", "ascending_west", "ascending_north", "ascending_east"),
    "ascending_west": ("ascending_west", "ascending_north", "ascending_east", "ascending_south"),
    "north_east": ("north_east", "south_east", "south_west", "north_west"),
    "south_east": ("south_east", "south_west", "north_west", "north_east"),
    "south_west": ("south_west", "north_west", "north_east", "south_east"),
    "north_west": ("north_west", "north_east", "south_east", "south_west"),
}


def _sha(lines: list[str]) -> str:
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _split_state(state: str) -> tuple[str, list[tuple[str, str]]]:
    state = canonical_block_state(state)
    if not state.endswith("]") or "[" not in state:
        return state, []
    base, raw = state.split("[", 1)
    props = []
    for part in raw[:-1].split(","):
        key, _, value = part.partition("=")
        props.append((key, value))
    return base, props


def _rotate_cardinal(value: str, quarter_turns: int) -> str:
    if value not in _CARDINAL_SET:
        return value
    return _CARDINAL[(_CARDINAL.index(value) + quarter_turns) % 4]


def _rotate_direction_tokens(value: str, quarter_turns: int) -> str:
    return _DIRECTION_TOKEN.sub(lambda match: _rotate_cardinal(match.group(1), quarter_turns), value)


def rotate_block_state(state: str, quarter_turns: int) -> str:
    """Rotate common and generic directional state properties around Y.

    Cardinal property keys are rotated too, covering fences/walls/panes and many modded
    connection states. Cardinal tokens inside values are rotated generically, while rail
    shapes and 0..15 ``rotation`` properties receive their Minecraft-specific treatment.
    """
    turns = quarter_turns % 4
    if turns == 0:
        return canonical_block_state(state)

    base, props = _split_state(state)
    rotated: list[tuple[str, str]] = []
    for key, value in props:
        new_key = _rotate_cardinal(key, turns)
        if key == "axis" and value in {"x", "z"} and turns % 2:
            new_value = "z" if value == "x" else "x"
        elif key == "rotation" and value.isdigit():
            new_value = str((int(value) + 4 * turns) % 16)
        elif key == "shape" and value in _RAIL_SHAPES:
            new_value = _RAIL_SHAPES[value][turns]
        else:
            new_value = _rotate_direction_tokens(value, turns)
        rotated.append((new_key, new_value))

    if not rotated:
        return base
    body = ",".join(f"{key}={value}" for key, value in sorted(rotated))
    return f"{base}[{body}]"


def rotate_structure(structure: CanonicalStructure, quarter_turns: int) -> CanonicalStructure:
    turns = quarter_turns % 4
    width, height, length = structure.dimensions
    if turns == 0:
        return structure

    occupied_width = max(block.x for block in structure.blocks) + 1
    occupied_length = max(block.z for block in structure.blocks) + 1
    rotated_rows: list[tuple[int, int, int, str, int | str | None]] = []
    for block in structure.blocks:
        if turns == 1:
            x, z = occupied_length - 1 - block.z, block.x
        elif turns == 2:
            x, z = occupied_width - 1 - block.x, occupied_length - 1 - block.z
        else:
            x, z = block.z, occupied_width - 1 - block.x
        rotated_rows.append(
            (x, block.y, z, rotate_block_state(block.state, turns), block.source_state_id)
        )

    rotated_dimensions = (length, height, width) if turns % 2 else structure.dimensions
    blocks = tuple(
        sorted(
            (
                CanonicalBlock(x, y, z, state, source_state_id)
                for x, y, z, state, source_state_id in rotated_rows
            ),
            key=lambda block: (block.x, block.y, block.z, block.state, str(block.source_state_id)),
        )
    )
    return CanonicalStructure(
        blocks=blocks,
        dimensions=rotated_dimensions,
        minecraft_version=structure.minecraft_version,
        metadata=dict(structure.metadata),
    )


def exact_hash(structure: CanonicalStructure) -> str:
    lines = []
    for block in structure.blocks:
        opaque = "" if block.source_state_id is None else f"|source_state_id={block.source_state_id}"
        lines.append(f"{block.x},{block.y},{block.z},{block.state}{opaque}")
    return _sha(lines)


def occupancy_hash(structure: CanonicalStructure) -> str:
    return _sha([f"{b.x},{b.y},{b.z}" for b in structure.blocks])


def rotation_hash(structure: CanonicalStructure) -> str:
    return min(exact_hash(rotate_structure(structure, turns)) for turns in range(4))


def structure_hashes(structure: CanonicalStructure) -> StructureHashes:
    return StructureHashes(
        structure_hash=exact_hash(structure),
        rotation_hash=rotation_hash(structure),
        occupancy_hash=occupancy_hash(structure),
    )
