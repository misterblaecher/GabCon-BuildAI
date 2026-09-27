"""Structural validation for block combinations that Minecraft expects to be paired."""

from __future__ import annotations

from mcbuild import palette
from mcbuild.registry_structures import classify_structure
from mcbuild.voxel import Coord, VoxelGrid

_DIRECTION_OFFSETS: dict[str, Coord] = {
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
    "up": (0, 1, 0),
    "down": (0, -1, 0),
}
_AXIS_OFFSETS: dict[str, Coord] = {
    "x": (1, 0, 0),
    "y": (0, 1, 0),
    "z": (0, 0, 1),
}
_POSITIVE_DIRECTIONS = {"east", "south", "up"}
_CREATE_CHAIN_DRIVES = {
    "create:adjustable_chain_gearshift",
    "create:encased_chain_drive",
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


def _negate(delta: Coord) -> Coord:
    return -delta[0], -delta[1], -delta[2]


def _state_mismatches(left: dict[str, str], right: dict[str, str], ignore: set[str]) -> list[str]:
    keys = (set(left) | set(right)) - ignore
    return sorted(key for key in keys if left.get(key) != right.get(key))


def _block_state_at(grid: VoxelGrid, coord: Coord):
    idx = grid.get(*coord)
    if idx is None:
        return None, None
    block = palette.get_block_by_index(idx)
    entry = palette.registry_block_entry(block.base_id)
    if entry is None:
        return block, dict(block.state)
    return block, _effective_state(block, entry)


def _validate_vertical_pair(grid: VoxelGrid, block_id: str, lower_coord: Coord, errors: list[str]) -> None:
    upper_coord = _coord_add(lower_coord, (0, 1, 0))
    lower_idx = grid.get(*lower_coord)
    upper_idx = grid.get(*upper_coord)

    if lower_idx is None or upper_idx is None:
        missing = "lower" if lower_idx is None else "upper"
        missing_coord = lower_coord if lower_idx is None else upper_coord
        errors.append(
            f"{block_id} requires lower+upper halves; {missing} half is missing at "
            f"({missing_coord[0]},{missing_coord[1]},{missing_coord[2]})."
        )
        return

    lower = palette.get_block_by_index(lower_idx)
    upper = palette.get_block_by_index(upper_idx)
    lower_entry = palette.registry_block_entry(lower.base_id)
    upper_entry = palette.registry_block_entry(upper.base_id)
    if lower.base_id != block_id or upper.base_id != block_id or lower_entry is None or upper_entry is None:
        errors.append(
            f"{block_id} requires matching halves at {lower_coord} and {upper_coord}; "
            f"found {lower.mc_id} / {upper.mc_id}."
        )
        return

    lower_state = _effective_state(lower, lower_entry)
    upper_state = _effective_state(upper, upper_entry)
    if lower_state.get("half") != "lower" or upper_state.get("half") != "upper":
        errors.append(
            f"{block_id} requires half=lower at {lower_coord} and half=upper at {upper_coord}; "
            f"found half={lower_state.get('half')} / half={upper_state.get('half')}."
        )
        return

    mismatches = _state_mismatches(lower_state, upper_state, {"half"})
    if mismatches:
        errors.append(
            f"{block_id} halves at {lower_coord}/{upper_coord} disagree on state properties: {', '.join(mismatches)}."
        )


def _validate_head_foot_pair(
    grid: VoxelGrid,
    block_id: str,
    foot_coord: Coord,
    facing: str,
    errors: list[str],
) -> None:
    offset = _DIRECTION_OFFSETS.get(facing)
    if offset is None:
        errors.append(f"{block_id} at {foot_coord} has unsupported facing={facing!r}.")
        return

    head_coord = _coord_add(foot_coord, offset)
    foot_idx = grid.get(*foot_coord)
    head_idx = grid.get(*head_coord)
    if foot_idx is None or head_idx is None:
        missing = "foot" if foot_idx is None else "head"
        missing_coord = foot_coord if foot_idx is None else head_coord
        errors.append(
            f"{block_id} requires foot+head parts; {missing} part is missing at "
            f"({missing_coord[0]},{missing_coord[1]},{missing_coord[2]})."
        )
        return

    foot = palette.get_block_by_index(foot_idx)
    head = palette.get_block_by_index(head_idx)
    foot_entry = palette.registry_block_entry(foot.base_id)
    head_entry = palette.registry_block_entry(head.base_id)
    if foot.base_id != block_id or head.base_id != block_id or foot_entry is None or head_entry is None:
        errors.append(
            f"{block_id} requires matching foot/head parts at {foot_coord} and {head_coord}; "
            f"found {foot.mc_id} / {head.mc_id}."
        )
        return

    foot_state = _effective_state(foot, foot_entry)
    head_state = _effective_state(head, head_entry)
    if foot_state.get("part") != "foot" or head_state.get("part") != "head":
        errors.append(
            f"{block_id} requires part=foot at {foot_coord} and part=head at {head_coord}; "
            f"found part={foot_state.get('part')} / part={head_state.get('part')}."
        )
        return

    mismatches = _state_mismatches(foot_state, head_state, {"part"})
    if mismatches:
        errors.append(
            f"{block_id} foot/head at {foot_coord}/{head_coord} disagree on state properties: {', '.join(mismatches)}."
        )


def _chain_connection_axis(state: dict[str, str]) -> str | None:
    axis = state.get("axis")
    along_first = state.get("axis_along_first") == "true"
    if axis not in _AXIS_OFFSETS:
        return None
    if along_first:
        return "y" if axis == "x" else "x"
    return "y" if axis == "z" else "z"


def _chain_neighbor_connects(grid: VoxelGrid, coord: Coord, connection_axis: str) -> bool:
    block, state = _block_state_at(grid, coord)
    if block is None or block.base_id not in _CREATE_CHAIN_DRIVES or state is None:
        return False
    if state.get("axis") == connection_axis:
        return False
    other_part = state.get("part")
    return other_part == "none" or _chain_connection_axis(state) == connection_axis


def _validate_chain_drive_line(
    grid: VoxelGrid,
    block_id: str,
    coord: Coord,
    state: dict[str, str],
    errors: list[str],
) -> None:
    part = state.get("part")
    connection_axis = _chain_connection_axis(state)
    if part not in {"start", "middle", "end", "none"} or connection_axis is None:
        return

    offset = _AXIS_OFFSETS[connection_axis]
    negative = _chain_neighbor_connects(grid, _coord_sub(coord, offset), connection_axis)
    positive = _chain_neighbor_connects(grid, _coord_add(coord, offset), connection_axis)
    expected = {
        "none": (False, False),
        "start": (False, True),
        "end": (True, False),
        "middle": (True, True),
    }[part]

    if (negative, positive) != expected:
        errors.append(
            f"{block_id} at {coord} has part={part} but chain-drive neighbors on axis {connection_axis} are "
            f"negative={negative}, positive={positive}; expected negative={expected[0]}, positive={expected[1]}."
        )


def _gantry_neighbor_connects(grid: VoxelGrid, coord: Coord, facing: str) -> bool:
    block, state = _block_state_at(grid, coord)
    return (
        block is not None
        and block.base_id == "create:gantry_shaft"
        and state is not None
        and state.get("facing") == facing
    )


def _validate_gantry_line(grid: VoxelGrid, coord: Coord, state: dict[str, str], errors: list[str]) -> None:
    part = state.get("part")
    facing = state.get("facing")
    offset = _DIRECTION_OFFSETS.get(facing or "")
    if part not in {"start", "middle", "end", "single"} or offset is None:
        return

    behind = _gantry_neighbor_connects(grid, _coord_sub(coord, offset), facing)
    ahead = _gantry_neighbor_connects(grid, _coord_add(coord, offset), facing)
    expected = {
        "single": (False, False),
        "start": (False, True),
        "end": (True, False),
        "middle": (True, True),
    }[part]

    if (behind, ahead) != expected:
        errors.append(
            f"create:gantry_shaft at {coord} has part={part} but matching neighbors are "
            f"behind={behind}, ahead={ahead}; expected behind={expected[0]}, ahead={expected[1]}."
        )


def _belt_next_coord(state: dict[str, str], coord: Coord, forward: bool) -> Coord | None:
    part = state.get("part")
    facing = state.get("facing")
    slope = state.get("slope")
    direction = _DIRECTION_OFFSETS.get(facing or "")
    if direction is None:
        return None

    if part == "end" and forward:
        return None
    if part == "start" and not forward:
        return None

    step = 1 if forward else -1
    if slope == "vertical":
        vertical = step if facing in _POSITIVE_DIRECTIONS else -step
        return _coord_add(coord, (0, vertical, 0))

    moved = _coord_add(coord, direction if forward else _negate(direction))
    if slope == "upward":
        return _coord_add(moved, (0, step, 0))
    if slope == "downward":
        return _coord_add(moved, (0, -step, 0))
    return moved


def _validate_belt_chain(grid: VoxelGrid, coord: Coord, state: dict[str, str], errors: list[str]) -> None:
    part = state.get("part")
    if part not in {"start", "middle", "end", "pulley"}:
        return

    directions = [True] if part == "start" else [False] if part == "end" else [False, True]
    for forward in directions:
        target = _belt_next_coord(state, coord, forward)
        if target is None:
            errors.append(f"create:belt at {coord} has part={part} but its required segment direction is invalid.")
            continue

        other, other_state = _block_state_at(grid, target)
        side = "next" if forward else "previous"
        if other is None or other.base_id != "create:belt" or other_state is None:
            errors.append(f"create:belt at {coord} is missing its {side} belt segment at {target}.")
            continue

        back = _belt_next_coord(other_state, target, not forward)
        if back != coord:
            errors.append(
                f"create:belt at {coord} points to {target}, but that segment does not point back "
                f"(facing={other_state.get('facing')}, slope={other_state.get('slope')}, "
                f"part={other_state.get('part')})."
            )


def _validate_vanilla_piston(
    block_id: str,
    grid: VoxelGrid,
    coord: Coord,
    state: dict[str, str],
    errors: list[str],
) -> None:
    if state.get("extended") != "true":
        return
    facing = state.get("facing")
    offset = _DIRECTION_OFFSETS.get(facing or "")
    if offset is None:
        return

    head_coord = _coord_add(coord, offset)
    head, head_state = _block_state_at(grid, head_coord)
    expected_type = "sticky" if block_id == "minecraft:sticky_piston" else "normal"
    if head is None or head.base_id != "minecraft:piston_head" or head_state is None:
        errors.append(f"{block_id} at {coord} is extended but minecraft:piston_head is missing at {head_coord}.")
        return
    if head_state.get("facing") != facing or head_state.get("type") != expected_type:
        errors.append(
            f"{block_id} at {coord} requires piston_head[facing={facing},type={expected_type}] at {head_coord}; "
            f"found {head.mc_id}."
        )


def _direction_axis(facing: str) -> str | None:
    if facing in {"east", "west"}:
        return "x"
    if facing in {"up", "down"}:
        return "y"
    if facing in {"north", "south"}:
        return "z"
    return None


def _validate_create_mechanical_piston(
    block_id: str,
    grid: VoxelGrid,
    coord: Coord,
    state: dict[str, str],
    errors: list[str],
) -> None:
    piston_state = state.get("state")
    if piston_state == "moving":
        errors.append(
            f"{block_id} at {coord} uses transient state=moving, which cannot be represented as a static schematic."
        )
        return
    if piston_state != "extended":
        return

    facing = state.get("facing")
    offset = _DIRECTION_OFFSETS.get(facing or "")
    axis = _direction_axis(facing or "")
    if offset is None or axis is None:
        return

    expected_type = "sticky" if block_id == "create:sticky_mechanical_piston" else "normal"
    current = _coord_add(coord, offset)
    while True:
        block, current_state = _block_state_at(grid, current)
        if block is None or current_state is None:
            errors.append(
                f"{block_id} at {coord} is extended but no create:mechanical_piston_head was found "
                f"along facing={facing}; chain ended at {current}."
            )
            return

        if block.base_id == "create:piston_extension_pole":
            if _direction_axis(current_state.get("facing", "")) != axis:
                errors.append(
                    f"{block_id} at {coord} has a misaligned piston_extension_pole at {current}: {block.mc_id}."
                )
                return
            current = _coord_add(current, offset)
            continue

        if block.base_id == "create:mechanical_piston_head":
            if current_state.get("facing") != facing or current_state.get("type") != expected_type:
                errors.append(
                    f"{block_id} at {coord} requires mechanical_piston_head[facing={facing},type={expected_type}] "
                    f"at the end of its extension; found {block.mc_id} at {current}."
                )
            return

        errors.append(
            f"{block_id} at {coord} is extended but {block.mc_id} at {current} interrupts the "
            "piston_extension_pole/head chain."
        )
        return


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

            key = (block.base_id, rule_name, coord)
            if key in checked:
                continue
            checked.add(key)

            if rule_name == "vertical_pair":
                half = state.get("half")
                if half in {"lower", "upper"}:
                    lower_coord = coord if half == "lower" else _coord_sub(coord, (0, 1, 0))
                    pair_key = (block.base_id, rule_name, lower_coord)
                    if pair_key != key and pair_key in checked:
                        continue
                    checked.add(pair_key)
                    _validate_vertical_pair(grid, block.base_id, lower_coord, errors)
                continue

            if rule_name == "horizontal_head_foot_pair":
                part = state.get("part")
                facing = state.get("facing")
                offset = _DIRECTION_OFFSETS.get(facing or "")
                if part in {"foot", "head"} and offset is not None:
                    foot_coord = coord if part == "foot" else _coord_sub(coord, offset)
                    pair_key = (block.base_id, rule_name, foot_coord)
                    if pair_key != key and pair_key in checked:
                        continue
                    checked.add(pair_key)
                    _validate_head_foot_pair(grid, block.base_id, foot_coord, facing, errors)
                continue

            if rule_name == "create_chain_drive_line":
                _validate_chain_drive_line(grid, block.base_id, coord, state, errors)
            elif rule_name == "create_gantry_shaft_line":
                _validate_gantry_line(grid, coord, state, errors)
            elif rule_name == "create_belt_chain":
                _validate_belt_chain(grid, coord, state, errors)
            elif rule_name == "vanilla_piston":
                _validate_vanilla_piston(block.base_id, grid, coord, state, errors)
            elif rule_name == "create_mechanical_piston":
                _validate_create_mechanical_piston(block.base_id, grid, coord, state, errors)
            elif rule_name == "state_only_extension":
                continue

    return errors


def _raise_structural_errors(errors: list[str]) -> None:
    if not errors:
        return
    preview = "\n".join(f"  - {error}" for error in errors[:8])
    suffix = f"\n  ... and {len(errors) - 8} more" if len(errors) > 8 else ""
    raise BuildValidationError(
        "Incomplete or inconsistent multi-block structure(s):\n"
        f"{preview}{suffix}\n"
        "Place every required part explicitly with compatible states before exporting the schematic."
    )


def validate_structural_blocks(grid: VoxelGrid) -> None:
    """Validate every registry-inferred multi-block rule that has reviewed geometry."""
    _raise_structural_errors(_collect_structural_errors(grid))


def validate_double_height_blocks(grid: VoxelGrid) -> None:
    """Backward-compatible validator for half=lower|upper blocks only."""
    _raise_structural_errors(_collect_structural_errors(grid, {"vertical_pair"}))
