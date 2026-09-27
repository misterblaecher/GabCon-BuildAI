"""Generate a server-registry compatibility lab for paste-testing blocks in game."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mcbuild import palette
from mcbuild.export.schem import export_schem
from mcbuild.gallery import generate_index
from mcbuild.profile import ServerProfile, resolve_registry_path
from mcbuild.registry_structures import classify_structure
from mcbuild.render.views import build_contact_sheet, build_stats
from mcbuild.validation import validate_structural_blocks
from mcbuild.voxel import Coord, VoxelGrid

DEFAULT_OUT = Path("generated") / "03-global-registry-lab"
DEFAULT_COLUMNS = 24
SLOT_SPACING = 4

DEFAULT_VIEWS = [
    {"yaw": 0},
    {"yaw": 1},
    {"mode": "top-down"},
]

VANILLA_FIXTURES = (
    "minecraft:stone_bricks",
    "minecraft:stone_brick_stairs",
    "minecraft:stone_brick_slab",
    "minecraft:stone_brick_wall",
    "minecraft:oak_fence",
    "minecraft:oak_fence_gate",
    "minecraft:glass_pane",
    "minecraft:iron_bars",
    "minecraft:oak_door",
    "minecraft:oak_trapdoor",
    "minecraft:red_bed",
    "minecraft:chest",
    "minecraft:barrel",
    "minecraft:hopper",
    "minecraft:furnace",
    "minecraft:blast_furnace",
    "minecraft:smoker",
    "minecraft:brewing_stand",
    "minecraft:enchanting_table",
    "minecraft:beacon",
    "minecraft:spawner",
    "minecraft:ender_chest",
    "minecraft:shulker_box",
    "minecraft:decorated_pot",
    "minecraft:chiseled_bookshelf",
    "minecraft:lectern",
    "minecraft:oak_sign",
    "minecraft:oak_wall_sign",
    "minecraft:oak_hanging_sign",
    "minecraft:oak_wall_hanging_sign",
    "minecraft:piston",
    "minecraft:sticky_piston",
    "minecraft:rail",
    "minecraft:powered_rail",
    "minecraft:ladder",
    "minecraft:torch",
    "minecraft:wall_torch",
    "minecraft:lantern",
    "minecraft:redstone_wire",
    "minecraft:repeater",
    "minecraft:comparator",
    "minecraft:observer",
    "minecraft:dispenser",
    "minecraft:dropper",
)

_NAMESPACE_SUPPORT = {
    "minecraft": "minecraft:light_gray_concrete",
    "create": "minecraft:orange_concrete",
    "create_dragons_plus": "minecraft:purple_concrete",
    "create_enchantment_industry": "minecraft:magenta_concrete",
    "sophisticatedbackpacks": "minecraft:yellow_concrete",
    "trading_floor": "minecraft:lime_concrete",
    "waystones": "minecraft:blue_concrete",
}

_DIRECTION: dict[str, Coord] = {
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
    "up": (0, 1, 0),
    "down": (0, -1, 0),
}


def _parse_state(state: str) -> tuple[str, dict[str, str]]:
    if "[" not in state or not state.endswith("]"):
        return state, {}
    block_id, raw = state.split("[", 1)
    props: dict[str, str] = {}
    for item in raw[:-1].split(","):
        key, sep, value = item.partition("=")
        if sep:
            props[key] = value
    return block_id, props


def _format_state(block_id: str, props: dict[str, str]) -> str:
    if not props:
        return block_id
    body = ",".join(f"{key}={value}" for key, value in sorted(props.items()))
    return f"{block_id}[{body}]"


def _state_candidates(entry: dict[str, Any]) -> list[tuple[str, dict[str, str]]]:
    return [(state, _parse_state(state)[1]) for state in entry["states"]]


_SAFE_PREFERENCES = {
    "attached": "false",
    "enabled": "true",
    "extended": "false",
    "face": "floor",
    "facing": "north",
    "hanging": "false",
    "lit": "false",
    "locked": "false",
    "occupied": "false",
    "open": "false",
    "powered": "false",
    "state": "retracted",
    "triggered": "false",
    "waterlogged": "false",
}


def _pick_state(entry: dict[str, Any], required: dict[str, str] | None = None) -> str | None:
    required = required or {}
    candidates = []
    for state, props in _state_candidates(entry):
        if any(props.get(key) != value for key, value in required.items()):
            continue
        score = sum(props.get(key) == value for key, value in _SAFE_PREFERENCES.items())
        candidates.append((score, state))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][1]


def _matching_state(entry: dict[str, Any], source: str, changes: dict[str, str]) -> str | None:
    block_id, props = _parse_state(source)
    props.update(changes)
    for state, candidate_props in _state_candidates(entry):
        if candidate_props == props:
            return state
    candidate = _format_state(block_id, props)
    return candidate if candidate in entry["states"] else None


def _is_flowing_fluid(entry: dict[str, Any]) -> bool:
    properties = entry.get("properties", {})
    if set(properties) != {"level"}:
        return False
    levels = {str(value) for value in properties.get("level", [])}
    return "0" in levels and "15" in levels


def _support_id(profile: ServerProfile, namespace: str) -> str:
    preferred = _NAMESPACE_SUPPORT.get(namespace, "minecraft:smooth_stone")
    if preferred in profile.blocks:
        return preferred
    if "minecraft:smooth_stone" in profile.blocks:
        return "minecraft:smooth_stone"
    return next(iter(profile.blocks))


def _state_support_offsets(block_id: str, state: str) -> list[Coord]:
    _, props = _parse_state(state)
    path = block_id.split(":", 1)[1]
    offsets: list[Coord] = []

    if props.get("face") == "ceiling" or props.get("hanging") == "true" or path.endswith("_hanging_sign"):
        offsets.append((0, 1, 0))

    wall_like = (
        props.get("face") == "wall"
        or "_wall_" in path
        or path.startswith("wall_")
        or path.endswith("_wall_sign")
        or path.endswith("_wall_banner")
        or path.endswith("_wall_torch")
        or path.endswith("_ladder")
        or path == "ladder"
    )
    facing = props.get("facing")
    if wall_like and facing in _DIRECTION:
        direction = _DIRECTION[facing]
        offsets.append((-direction[0], 0, -direction[2]))

    return offsets


def _build_structure_states(block_id: str, entry: dict[str, Any]) -> tuple[list[tuple[Coord, str]], str | None]:
    rules = classify_structure(block_id, entry)
    manual = [rule for rule in rules if rule["status"] == "manual_review"]
    if manual:
        names = ", ".join(str(rule["rule"]) for rule in manual)
        return [], f"manual structural rule: {names}"

    rule_names = {str(rule["rule"]) for rule in rules}

    if "vertical_pair" in rule_names:
        lower = _pick_state(entry, {"half": "lower"})
        if lower is None:
            return [], "could not find half=lower state"
        upper = _matching_state(entry, lower, {"half": "upper"})
        if upper is None:
            return [], "could not find matching half=upper state"
        return [((0, 0, 0), lower), ((0, 1, 0), upper)], None

    if "horizontal_head_foot_pair" in rule_names:
        foot = _pick_state(entry, {"part": "foot", "facing": "east"})
        if foot is None:
            foot = _pick_state(entry, {"part": "foot"})
        if foot is None:
            return [], "could not find part=foot state"
        _, props = _parse_state(foot)
        facing = props.get("facing")
        direction = _DIRECTION.get(facing or "")
        if direction is None:
            return [], f"unsupported head/foot facing={facing!r}"
        head = _matching_state(entry, foot, {"part": "head"})
        if head is None:
            return [], "could not find matching part=head state"
        return [((0, 0, 0), foot), (direction, head)], None

    if "create_belt_chain" in rule_names:
        start = _pick_state(entry, {"part": "start", "slope": "horizontal", "facing": "east"})
        if start is None:
            start = _pick_state(entry, {"part": "start", "slope": "horizontal"})
        if start is None:
            return [], "could not find horizontal belt start state"
        _, props = _parse_state(start)
        facing = props.get("facing")
        direction = _DIRECTION.get(facing or "")
        if direction is None:
            return [], f"unsupported belt facing={facing!r}"
        end = _matching_state(entry, start, {"part": "end"})
        if end is None:
            return [], "could not find matching belt end state"
        return [((0, 0, 0), start), (direction, end)], None

    required_by_rule = {
        "create_chain_drive_line": {"part": "none"},
        "create_gantry_shaft_line": {"part": "single"},
        "vanilla_piston": {"extended": "false"},
        "create_mechanical_piston": {"state": "retracted"},
        "state_only_extension": {"extended": "false"},
    }
    for rule_name, required in required_by_rule.items():
        if rule_name in rule_names:
            state = _pick_state(entry, required)
            if state is None:
                return [], f"could not find safe state for {rule_name}"
            return [((0, 0, 0), state)], None

    state = _pick_state(entry)
    if state is None:
        return [], "registry entry has no usable state"
    return [((0, 0, 0), state)], None


def _selected_block_ids(profile: ServerProfile, all_blocks: bool) -> list[str]:
    if all_blocks:
        return sorted(profile.blocks)

    modded = [block_id for block_id in profile.blocks if not block_id.startswith("minecraft:")]
    fixtures = [block_id for block_id in VANILLA_FIXTURES if block_id in profile.blocks]
    return sorted(modded) + fixtures


def build_registry_lab(
    profile: ServerProfile,
    *,
    all_blocks: bool = False,
    columns: int = DEFAULT_COLUMNS,
) -> tuple[VoxelGrid, dict[str, Any]]:
    if columns < 4:
        raise ValueError("columns must be at least 4")

    palette.configure_server_profile(profile)
    grid = VoxelGrid()
    layout: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    tested_by_namespace: Counter[str] = Counter()
    unrenderable: list[str] = []

    selected = _selected_block_ids(profile, all_blocks)
    groups: dict[str, list[str]] = {}
    for block_id in selected:
        groups.setdefault(block_id.split(":", 1)[0], []).append(block_id)

    row = 0
    for namespace in sorted(groups, key=lambda value: (value != "minecraft", value)):
        col = 0
        for block_id in groups[namespace]:
            entry = profile.blocks[block_id]
            if _is_flowing_fluid(entry):
                skipped.append({"block": block_id, "reason": "flowing fluid block"})
                continue

            states, reason = _build_structure_states(block_id, entry)
            if reason is not None:
                skipped.append({"block": block_id, "reason": reason})
                continue

            x = col * SLOT_SPACING
            z = row * SLOT_SPACING
            support_id = _support_id(profile, namespace)
            support_idx = palette.get_block(support_id).index
            placed_states: list[dict[str, Any]] = []

            for (dx, dy, dz), state in states:
                wx, wy, wz = x + dx, 1 + dy, z + dz
                block = palette.get_block(state)
                grid.set(wx, wy, wz, block.index)
                grid.set(wx, 0, wz, support_idx)
                if not block.renderable:
                    unrenderable.append(state)

                for sx, sy, sz in _state_support_offsets(block_id, state):
                    support_coord = (wx + sx, wy + sy, wz + sz)
                    if support_coord != (wx, wy, wz):
                        grid.set(*support_coord, support_idx)

                placed_states.append({"coord": [wx, wy, wz], "state": state, "renderable": block.renderable})

            layout.append(
                {
                    "block": block_id,
                    "namespace": namespace,
                    "origin": [x, 1, z],
                    "states": placed_states,
                }
            )
            tested_by_namespace[namespace] += 1

            col += 1
            if col >= columns:
                col = 0
                row += 1

        if col != 0:
            row += 1
        row += 1

    validate_structural_blocks(grid)

    manifest = {
        "format_version": 1,
        "scope": "all-registry-blocks" if all_blocks else "all-modded-plus-vanilla-fixtures",
        "minecraft_version": profile.minecraft_version,
        "data_version": profile.data_version,
        "registry_block_count": len(profile.blocks),
        "selected_block_count": len(selected),
        "tested_block_types": len(layout),
        "tested_by_namespace": dict(sorted(tested_by_namespace.items())),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "unrenderable_state_count": len(unrenderable),
        "unrenderable_states": sorted(set(unrenderable)),
        "columns": columns,
        "slot_spacing": SLOT_SPACING,
        "layout": layout,
    }
    return grid, manifest


def write_registry_lab(
    profile: ServerProfile,
    out_dir: Path,
    *,
    all_blocks: bool = False,
    columns: int = DEFAULT_COLUMNS,
    render: bool = True,
) -> dict[str, Any]:
    grid, manifest = build_registry_lab(profile, all_blocks=all_blocks, columns=columns)
    out_dir.mkdir(parents=True, exist_ok=True)

    schem_path = out_dir / "final.schem"
    stats_path = out_dir / "stats.json"
    layout_path = out_dir / "layout.json"
    render_path = out_dir / "render.png"

    export_schem(grid, str(schem_path))
    layout_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    stats = {
        "name": "Global Registry Compatibility Lab",
        "server_profile": palette.registry_metadata(),
        "compatibility": {
            "valid": True,
            "unknown_blocks": [],
            "invalid_states": [],
            "structural_validation": "passed",
        },
        "lab": {
            key: value for key, value in manifest.items() if key not in {"layout", "skipped", "unrenderable_states"}
        },
        **build_stats(grid),
    }

    labels: list[str] = []
    if render:
        sheet, labels, _ = build_contact_sheet(grid, DEFAULT_VIEWS)
        sheet.save(render_path)
        stats["views"] = labels

    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    if out_dir.parent.name == "generated" and render:
        generate_index(out_dir.parent)

    return {
        "grid": grid,
        "manifest": manifest,
        "schem": schem_path,
        "stats": stats_path,
        "layout": layout_path,
        "render": render_path if render else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a paste-test lab from the live server registry. By default it covers every modded block "
            "plus a focused vanilla geometry/BlockEntity fixture set."
        )
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Server block-registry JSON. Defaults to MCBUILD_SERVER_REGISTRY.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output directory. Defaults to {DEFAULT_OUT}.",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=DEFAULT_COLUMNS,
        help=f"Test slots per row. Defaults to {DEFAULT_COLUMNS}.",
    )
    parser.add_argument(
        "--all-blocks",
        action="store_true",
        help=(
            "Test every registry block, including all vanilla blocks. Default is all modded blocks + vanilla fixtures."
        ),
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip the contact-sheet preview and only write the schematic/reports.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    registry_path = resolve_registry_path(args.registry)
    if registry_path is None:
        print("ERROR: No server registry configured. Set MCBUILD_SERVER_REGISTRY or pass --registry.")
        return 1

    try:
        profile = ServerProfile.load(registry_path)
        result = write_registry_lab(
            profile,
            args.out,
            all_blocks=args.all_blocks,
            columns=args.columns,
            render=not args.no_render,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    manifest = result["manifest"]
    grid: VoxelGrid = result["grid"]
    dims = build_stats(grid)["dims"]

    print(f"Minecraft: {profile.minecraft_version} (DataVersion {profile.data_version})")
    print(f"Scope: {manifest['scope']}")
    print(f"Registry blocks: {manifest['registry_block_count']:,}")
    print(f"Block types selected: {manifest['selected_block_count']:,}")
    print(f"Block types tested: {manifest['tested_block_types']:,}")
    for namespace, count in manifest["tested_by_namespace"].items():
        print(f"  {namespace}: {count:,}")
    print(f"Skipped: {manifest['skipped_count']:,}")
    print(f"Unrenderable states: {manifest['unrenderable_state_count']:,}")
    if dims is not None:
        print(f"Dimensions: {'x'.join(str(value) for value in dims)}")
    if result["render"] is not None:
        print(f"Render: {result['render']}")
    print(f"Schematic: {result['schem']}")
    print(f"Layout: {result['layout']}")
    print(f"Stats: {result['stats']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
