"""Infer structural multi-block patterns from an exported live server registry."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mcbuild.profile import ProfileError, ServerProfile, resolve_registry_path

AUDIT_FORMAT_VERSION = 1
DEFAULT_AUDIT_PATH = Path(".mcbuild") / "structural-blocks.json"
_CARDINAL = {"north", "south", "west", "east"}


def classify_structure(block_id: str, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return registry-inferred structural rules/candidates for one block.

    Only signatures whose placement relation is unambiguous are marked validated.
    Other state shapes are emitted as manual_review so BuildAI does not guess at
    mod-specific adjacency semantics.
    """
    properties = entry.get("properties")
    if not isinstance(properties, dict):
        return []

    result: list[dict[str, Any]] = []

    half_values = properties.get("half")
    if isinstance(half_values, list) and set(half_values) == {"lower", "upper"}:
        result.append(
            {
                "block": block_id,
                "rule": "vertical_pair",
                "status": "validated",
                "property": "half",
                "parts": ["lower", "upper"],
                "offset": [0, 1, 0],
            }
        )

    part_values = properties.get("part")
    if isinstance(part_values, list):
        parts = set(part_values)
        facing_values = properties.get("facing")
        if parts == {"head", "foot"} and isinstance(facing_values, list) and _CARDINAL <= set(facing_values):
            result.append(
                {
                    "block": block_id,
                    "rule": "horizontal_head_foot_pair",
                    "status": "validated",
                    "property": "part",
                    "parts": ["foot", "head"],
                    "direction_property": "facing",
                }
            )
        elif {"start", "middle", "end"} <= parts:
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
    if isinstance(extended_values, list) and {"true", "false"} <= set(extended_values):
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
    if isinstance(state_values, list) and {"retracted", "extended"} <= set(state_values):
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
