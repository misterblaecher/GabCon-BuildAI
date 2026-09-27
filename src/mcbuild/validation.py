"""Structural validation for block combinations that Minecraft expects to be paired."""

from __future__ import annotations

from mcbuild import palette
from mcbuild.voxel import VoxelGrid


class BuildValidationError(ValueError):
    """Raised when a voxel build is structurally invalid for placement."""


def _default_state(entry: dict) -> dict[str, str]:
    value = entry.get("default_state")
    if not isinstance(value, str) or "[" not in value or not value.endswith("]"):
        return {}
    _, raw = value.split("[", 1)
    result: dict[str, str] = {}
    for part in raw[:-1].split(","):
        key, sep, val = part.partition("=")
        if sep:
            result[key] = val
    return result


def _effective_half(block, entry: dict) -> str | None:
    state = dict(block.state)
    if "half" in state:
        return state["half"]
    return _default_state(entry).get("half")


def validate_double_height_blocks(grid: VoxelGrid) -> None:
    """Reject orphaned blocks whose registry uses half=lower|upper.

    Minecraft uses this state shape for true two-block structures (doors, tall plants,
    Waystones, etc.). A schematic containing only one half often pastes successfully at
    first and is then immediately removed by neighbor updates.
    """
    errors: list[str] = []

    for (x, y, z), idx in grid.items():
        block = palette.get_block_by_index(idx)
        entry = palette.registry_block_entry(block.base_id)
        if entry is None:
            continue

        properties = entry.get("properties")
        if not isinstance(properties, dict):
            continue
        halves = properties.get("half")
        if not isinstance(halves, list) or set(halves) != {"lower", "upper"}:
            continue

        half = _effective_half(block, entry)
        if half not in {"lower", "upper"}:
            continue

        other_coord = (x, y + 1, z) if half == "lower" else (x, y - 1, z)
        other_idx = grid.get(*other_coord)
        if other_idx is None:
            errors.append(
                f"{block.base_id} at ({x},{y},{z}) is half={half} but its "
                f"{'upper' if half == 'lower' else 'lower'} half is missing at "
                f"({other_coord[0]},{other_coord[1]},{other_coord[2]})."
            )
            continue

        other = palette.get_block_by_index(other_idx)
        other_entry = palette.registry_block_entry(other.base_id)
        other_half = _effective_half(other, other_entry) if other_entry is not None else None
        expected = "upper" if half == "lower" else "lower"
        if other.base_id != block.base_id or other_half != expected:
            errors.append(
                f"{block.base_id} at ({x},{y},{z}) is half={half}; expected "
                f"{block.base_id}[half={expected}] at "
                f"({other_coord[0]},{other_coord[1]},{other_coord[2]}), found {other.mc_id}."
            )

    if errors:
        preview = "\n".join(f"  - {error}" for error in errors[:8])
        suffix = f"\n  ... and {len(errors) - 8} more" if len(errors) > 8 else ""
        raise BuildValidationError(
            "Incomplete double-height block structure(s):\n"
            f"{preview}{suffix}\n"
            "Place both halves explicitly before exporting the schematic."
        )
