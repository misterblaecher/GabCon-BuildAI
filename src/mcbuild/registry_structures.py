"""Infer structural multi-block patterns from an exported live server registry."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mcbuild.profile import ProfileError, ServerProfile, resolve_registry_path

AUDIT_FORMAT_VERSION = 2
DEFAULT_AUDIT_PATH = Path(".mcbuild") / "structural-blocks.json"
_CARDINAL = {"north", "south", "west", "east"}

_CREATE_CHAIN_DRIVES = {
    "create:adjustable_chain_gearshift",
    "create:encased_chain_drive",
}
_CREATE_MECHANICAL_PISTONS = {
    "create:mechanical_piston",
    "create:sticky_mechanical_piston",
}
_VANILLA_PISTONS = {
    "minecraft:piston",
    "minecraft:sticky_piston",
}


def _rule(block_id: str, name: str, property_name: str, parts: list[str], **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "block": block_id,
        "rule": name,
        "status": "validated",
        "property": property_name,
        "parts": parts,
    }
    result.update(extra)
    return result


def classify_structure(block_id: str, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return registry-inferred structural rules/candidates for one block.

    Known Create/vanilla state machines are mapped to reviewed rules. Unknown
    signatures remain manual_review rather than guessing mod-specific adjacency.
    """
    properties = entry.get("properties")
    if not isinstance(properties, dict):
        return []

    result: list[dict[str, Any]] = []

    half_values = properties.get("half")
    if isinstance(half_values, list) and set(half_values) == {"lower", "upper"}:
        result.append(
            _rule(
                block_id,
                "vertical_pair",
                "half",
                ["lower", "upper"],
                offset=[0, 1, 0],
            )
        )

    part_values = properties.get("part")
    handled_part = False
    if isinstance(part_values, list):
        parts = set(part_values)
        facing_values = properties.get("facing")
        if parts == {"head", "foot"} and isinstance(facing_values, list) and set(facing_values) >= _CARDINAL:
            result.append(
                _rule(
                    block_id,
                    "horizontal_head_foot_pair",
                    "part",
                    ["foot", "head"],
                    direction_property="facing",
                )
            )
            handled_part = True
        elif block_id in _CREATE_CHAIN_DRIVES and {"start", "middle", "end", "none"} <= parts:
            result.append(
                _rule(
                    block_id,
                    "create_chain_drive_line",
                    "part",
                    list(part_values),
                    family=sorted(_CREATE_CHAIN_DRIVES),
                    axis_property="axis",
                    connection_selector_property="axis_along_first",
                )
            )
            handled_part = True
        elif block_id == "create:belt" and {"start", "middle", "end", "pulley"} <= parts:
            result.append(
                _rule(
                    block_id,
                    "create_belt_chain",
                    "part",
                    list(part_values),
                    direction_property="facing",
                    slope_property="slope",
                )
            )
            handled_part = True
        elif block_id == "create:gantry_shaft" and {"start", "middle", "end", "single"} <= parts:
            result.append(
                _rule(
                    block_id,
                    "create_gantry_shaft_line",
                    "part",
                    list(part_values),
                    direction_property="facing",
                )
            )
            handled_part = True

        if not handled_part and {"start", "middle", "end"} <= parts:
            result.append(
                {
                    "block": block_id,
                    "rule": "linear_multipart",
                    "status": "manual_review",
                    "property": "part",
                    "parts": list(part_values),
                    "reason": "Length and adjacency cannot be inferred safely from registry states alone.",
                }
            )

    extended_values = properties.get("extended")
    handled_extended = False
    if isinstance(extended_values, list) and {"true", "false"} <= set(extended_values):
        if block_id == "create:sticker":
            result.append(
                _rule(
                    block_id,
                    "state_only_extension",
                    "extended",
                    list(extended_values),
                    reason="Create Sticker extension is rendered by the same block and has no companion block.",
                )
            )
            handled_extended = True
        elif block_id in _VANILLA_PISTONS:
            result.append(
                _rule(
                    block_id,
                    "vanilla_piston",
                    "extended",
                    list(extended_values),
                    direction_property="facing",
                    companion_block="minecraft:piston_head",
                    companion_type="sticky" if block_id == "minecraft:sticky_piston" else "normal",
                )
            )
            handled_extended = True

        if not handled_extended:
            result.append(
                {
                    "block": block_id,
                    "rule": "extension_state",
                    "status": "manual_review",
                    "property": "extended",
                    "parts": list(extended_values),
                    "reason": "An extended state can depend on a different companion block ID.",
                }
            )

    state_values = properties.get("state")
    handled_state = False
    if isinstance(state_values, list) and {"retracted", "extended"} <= set(state_values):
        if block_id in _CREATE_MECHANICAL_PISTONS:
            result.append(
                _rule(
                    block_id,
                    "create_mechanical_piston",
                    "state",
                    list(state_values),
                    direction_property="facing",
                    pole_block="create:piston_extension_pole",
                    companion_block="create:mechanical_piston_head",
                    companion_type="sticky" if block_id == "create:sticky_mechanical_piston" else "normal",
                    transient_states=["moving"],
                )
            )
            handled_state = True

        if not handled_state:
            result.append(
                {
                    "block": block_id,
                    "rule": "extension_state",
                    "status": "manual_review",
                    "property": "state",
                    "parts": list(state_values),
                    "reason": "Moving/extended mod machinery requires mod-specific adjacency semantics.",
                }
            )

    return result


def audit_server_profile(profile: ServerProfile) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    for block_id, entry in profile.blocks.items():
        rules.extend(classify_structure(block_id, entry))

    counts_by_rule = Counter(rule["rule"] for rule in rules)
    counts_by_status = Counter(rule["status"] for rule in rules)
    namespaces = Counter(rule["block"].split(":", 1)[0] for rule in rules)

    return {
        "format_version": AUDIT_FORMAT_VERSION,
        "minecraft_version": profile.minecraft_version,
        "data_version": profile.data_version,
        "registry_generated_at": profile.generated_at,
        "candidate_count": len(rules),
        "counts_by_status": dict(sorted(counts_by_status.items())),
        "counts_by_rule": dict(sorted(counts_by_rule.items())),
        "namespaces": dict(sorted(namespaces.items())),
        "rules": rules,
    }


def write_audit(audit: dict[str, Any], output: str | Path) -> Path:
    destination = Path(output).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return destination


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Audit an exported server registry for multi-block structural state patterns."
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
        default=DEFAULT_AUDIT_PATH,
        help=f"Audit JSON destination. Defaults to {DEFAULT_AUDIT_PATH}.",
    )
    args = parser.parse_args()

    registry = resolve_registry_path(args.registry)
    if registry is None:
        parser.error("No server registry configured. Set MCBUILD_SERVER_REGISTRY or pass --registry.")

    try:
        profile = ServerProfile.load(registry)
    except ProfileError as exc:
        parser.error(str(exc))

    audit = audit_server_profile(profile)
    output = write_audit(audit, args.out)

    print(f"Minecraft: {audit['minecraft_version']} (DataVersion {audit['data_version']})")
    print(f"Structural candidates: {audit['candidate_count']}")
    for rule, count in audit["counts_by_rule"].items():
        print(f"  {rule}: {count}")
    print(
        "Validated automatically: "
        f"{audit['counts_by_status'].get('validated', 0)}; "
        f"manual review: {audit['counts_by_status'].get('manual_review', 0)}"
    )
    print(f"Audit: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
