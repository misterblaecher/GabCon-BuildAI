"""Structural validation for block combinations that Minecraft expects to be paired."""

from __future__ import annotations

from mcbuild import palette
from mcbuild.registry_structures import classify_structure
from mcbuild.voxel import Coord, VoxelGrid

_CARDINAL_OFFSETS: dict[str, Coord] = {
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
}


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


def _effective_state(block, entry: dict) -> dict[str, str]:
    state = _default_state(entry)
    state.update(dict(block.state))
    return state


def _coord_add(coord: Coord, delta: Coord) -> Coord:
    return coord[0] + delta[0], coord[1] + delta[1], coord[2] + delta[2]


def _coord_sub(coord: Coord, delta: Coord) -> Coord:
    return coord[0] - delta[0], coord[1] - delta[1], coord[2] - delta[2]


def _state_mismatches(left: dict[str, str], right: dict[str, str], ignore: set[str]) -> list[str]:
    keys = (set(left) | set(right)) - ignore
    return sorted(key for key in keys if left.get(key) != right.get(key))


def _validate_vertical_pair(grid: VoxelGrid, block_id: str, lower_coord: Coord, errors: list[str]) -> None:
    upper_coord = _coord_add(lower_coord, (0, 1, 0))
    lower_idx = grid.get(*lower_coord)
    upper_idx = grid.get(*upper_coord)

    if lower_idx is None or upper_idx is None:
        missing = "lower" if lower_idx is None else "upper"
        missing_coord = lower_coord if lower_idx is None else upper_coord
        message = (
            f"{block_id} requires lower+upper halves; {missing} half is missing at "
            f"({missing_coord[0]},{missing_coord[1]},{missing_coord[2]})."
        )
        errors.append(message)
        return

    lower = palette.get_block_by_index(lower_idx)
    upper = palette.get_block_by_index(upper_idx)
    lower_entry = palette.registry_block_entry(lower.base_id)
    upper_entry = palette.registry_block_entry(upper.base_id)
    if lower.base_id != block_id or upper.base_id != block_id or lower_entry is None or upper_entry is None:
        message = (
            f"{block_id} requires matching halves at {lower_coord} and {upper_coord}; "
            f"found {lower.mc_id} / {upper.mc_id}."
        )
        errors.append(message)
        return

    lower_state = _effective_state(lower, lower_entry)
    upper_state = _effective_state(upper, upper_entry)
    if lower_state.get("half") != "lower" or upper_state.get("half") != "upper":
        message = (
            f"{block_id} requires half=lower at {lower_coord} and half=upper at {upper_coord}; "
            f"found half={lower_state.get('half')} / half={upper_state.get('half')}."
        )
        errors.append(message)
        return

    mismatches = _state_mismatches(lower_state, upper_state, {"half"})
    if mismatches:
        message = (
            f"{block_id} halves at {lower_coord}/{upper_coord} disagree on state properties: "
            f"{', '.join(mismatches)}."
        )
        errors.append(message)


def _validate_head_foot_pair(grid: VoxelGrid, block_id: str, foot_coord: Coord, facing: str, errors: list[str]) -> None:
    offset = _CARDINAL_OFFSETS.get(facing)
    if offset is None:
        errors.append(f"{block_id} at {foot_coord} has unsupported facing={facing!r}.")
        return

    head_coord = _coord_add(foot_coord, offset)
    foot_idx = grid.get(*foot_coord)
    head_idx = grid.get(*head_coord)
    if foot_idx is None or head_idx is None:
        missing = "foot" if foot_idx is None else "head"
        missing_coord = foot_coord if foot_idx is None else head_coord
        message = (
            f"{block_id} requires foot+head parts; {missing} part is missing at "
            f"({missing_coord[0]},{missing_coord[1]},{missing_coord[2]})."
        )
        errors.append(message)
        return

    foot = palette.get_block_by_index(foot_idx)
    head = palette.get_block_by_index(head_idx)
    foot_entry = palette.registry_block_entry(foot.base_id)
    head_entry = palette.registry_block_entry(head.base_id)
    if foot.base_id != block_id or head.base_id != block_id or foot_entry is None or head_entry is None:
        message = (
            f"{block_id} requires matching foot/head parts at {foot_coord} and {head_coord}; "
            f"found {foot.mc_id} / {head.mc_id}."
        )
        errors.append(message)
        return

    foot_state = _effective_state(foot, foot_entry)
    head_state = _effective_state(head, head_entry)
    if foot_state.get("part") != "foot" or head_state.get("part") != "head":
        message = (
            f"{block_id} requires part=foot at {foot_coord} and part=head at {head_coord}; "
            f"found part={foot_state.get('part')} / part={head_state.get('part')}."
        )
        errors.append(message)
        return

    mismatches = _state_mismatches(foot_state, head_state, {"part"})
    if mismatches:
        message = (
            f"{block_id} foot/head at {foot_coord}/{head_coord} disagree on state properties: "
            f"{', '.join(mismatches)}."
        )
        errors.append(message)


def _collect_structural_errors(grid: VoxelGrid, allowed_rules: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    checked: set[tuple[str, str, Coord]] = set()

    for coord, idx in grid.items():
        block = palette.get_block_by_index(idx)
        entry = palette.registry_block_entry(block.base_id)
        if entry is None:
            continue

        state = _effective_state(block, entry)
        for rule in classify_structure(block.base_id, entry):
            if rule["status"] != "validated":
                continue
            rule_name = str(rule["rule"])
            if allowed_rules is not None and rule_name not in allowed_rules:
                continue

            if rule_name == "vertical_pair":
                half = state.get("half")
                if half not in {"lower", "upper"}:
                    continue
                lower_coord = coord if half == "lower" else _coord_sub(coord, (0, 1, 0))
                key = (block.base_id, rule_name, lower_coord)
                if key in checked:
                    continue
                checked.add(key)
                _validate_vertical_pair(grid, block.base_id, lower_coord, errors)
                continue

            if rule_name == "horizontal_head_foot_pair":
                part = state.get("part")
                facing = state.get("facing")
                if part not in {"foot", "head"} or facing not in _CARDINAL_OFFSETS:
                    continue
                offset = _CARDINAL_OFFSETS[facing]
                foot_coord = coord if part == "foot" else _coord_sub(coord, offset)
                key = (block.base_id, rule_name, foot_coord)
                if key in checked:
                    continue
                checked.add(key)
                _validate_head_foot_pair(grid, block.base_id, foot_coord, facing, errors)

    return errors


def _raise_structural_errors(errors: list[str]) -> None:
    if not errors:
        return
    preview = "\n".join(f"  - {error}" for error in errors[:8])
    suffix = f"\n  ... and {len(errors) - 8} more" if len(errors) > 8 else ""
    message = (
        "Incomplete or inconsistent multi-block structure(s):\n"
        f"{preview}{suffix}\n"
        "Place every required part explicitly with compatible states before exporting the schematic."
    )
    raise BuildValidationError(message)


def validate_structural_blocks(grid: VoxelGrid) -> None:
    """Validate every registry-inferred multi-block rule that has unambiguous geometry."""
    _raise_structural_errors(_collect_structural_errors(grid))


def validate_double_height_blocks(grid: VoxelGrid) -> None:
    """Backward-compatible validator for half=lower|upper blocks only."""
    _raise_structural_errors(_collect_structural_errors(grid, {"vertical_pair"}))
