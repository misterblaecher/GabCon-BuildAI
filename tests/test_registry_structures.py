from pathlib import Path

import pytest

from mcbuild.profile import ServerProfile
from mcbuild.registry_structures import audit_server_profile, classify_structure


def _entry(properties):
    states = ["example:test"]
    if properties:
        state_parts = ",".join(f"{key}={values[0]}" for key, values in sorted(properties.items()))
        states = [f"example:test[{state_parts}]"]
    return {
        "namespace": "example",
        "path": "test",
        "properties": properties,
        "default_state": states[0],
        "states": states,
        "state_count": 1,
    }


def test_classifies_vertical_pair():
    rules = classify_structure(
        "waystones:waystone",
        _entry({"half": ["upper", "lower"], "facing": ["north", "south", "west", "east"]}),
    )

    assert rules[0]["rule"] == "vertical_pair"
    assert rules[0]["status"] == "validated"


def test_classifies_bed_head_foot_pair():
    rules = classify_structure(
        "minecraft:red_bed",
        _entry({"facing": ["north", "south", "west", "east"], "part": ["head", "foot"]}),
    )

    assert rules[0]["rule"] == "horizontal_head_foot_pair"
    assert rules[0]["status"] == "validated"


@pytest.mark.parametrize(
    ("block_id", "properties", "expected_rule"),
    [
        (
            "create:adjustable_chain_gearshift",
            {"axis": ["x"], "axis_along_first": ["true", "false"], "part": ["start", "middle", "end", "none"]},
            "create_chain_drive_line",
        ),
        (
            "create:encased_chain_drive",
            {"axis": ["x"], "axis_along_first": ["true", "false"], "part": ["start", "middle", "end", "none"]},
            "create_chain_drive_line",
        ),
        (
            "create:belt",
            {
                "facing": ["north", "south", "west", "east"],
                "part": ["start", "middle", "end", "pulley"],
                "slope": ["horizontal", "upward", "downward", "vertical", "sideways"],
            },
            "create_belt_chain",
        ),
        (
            "create:gantry_shaft",
            {
                "facing": ["north", "east", "south", "west", "up", "down"],
                "part": ["start", "middle", "end", "single"],
            },
            "create_gantry_shaft_line",
        ),
        (
            "create:mechanical_piston",
            {"facing": ["north", "east", "south", "west", "up", "down"], "state": ["retracted", "moving", "extended"]},
            "create_mechanical_piston",
        ),
        (
            "create:sticky_mechanical_piston",
            {"facing": ["north", "east", "south", "west", "up", "down"], "state": ["retracted", "moving", "extended"]},
            "create_mechanical_piston",
        ),
        (
            "create:sticker",
            {"extended": ["true", "false"], "facing": ["north", "east", "south", "west", "up", "down"]},
            "state_only_extension",
        ),
        (
            "minecraft:piston",
            {"extended": ["true", "false"], "facing": ["north", "east", "south", "west", "up", "down"]},
            "vanilla_piston",
        ),
        (
            "minecraft:sticky_piston",
            {"extended": ["true", "false"], "facing": ["north", "east", "south", "west", "up", "down"]},
            "vanilla_piston",
        ),
    ],
)
def test_known_manual_review_cases_are_validated(block_id, properties, expected_rule):
    rules = classify_structure(block_id, _entry(properties))

    assert len(rules) == 1
    assert rules[0]["rule"] == expected_rule
    assert rules[0]["status"] == "validated"


def test_unknown_linear_machine_stays_manual_review():
    rules = classify_structure(
        "example:linear_machine",
        _entry({"part": ["start", "middle", "end", "none"]}),
    )

    assert rules[0]["rule"] == "linear_multipart"
    assert rules[0]["status"] == "manual_review"


def test_unknown_extension_machine_stays_manual_review():
    rules = classify_structure(
        "example:pistonish",
        _entry({"extended": ["true", "false"], "facing": ["north", "south"]}),
    )

    assert rules[0]["rule"] == "extension_state"
    assert rules[0]["status"] == "manual_review"


def test_audit_marks_current_nine_reviewed_cases_as_validated():
    blocks = {
        "create:adjustable_chain_gearshift": _entry(
            {"axis": ["x"], "axis_along_first": ["true", "false"], "part": ["start", "middle", "end", "none"]}
        ),
        "create:encased_chain_drive": _entry(
            {"axis": ["x"], "axis_along_first": ["true", "false"], "part": ["start", "middle", "end", "none"]}
        ),
        "create:belt": _entry(
            {
                "facing": ["north", "south", "west", "east"],
                "part": ["start", "middle", "end", "pulley"],
                "slope": ["horizontal", "upward", "downward", "vertical", "sideways"],
            }
        ),
        "create:gantry_shaft": _entry(
            {
                "facing": ["north", "east", "south", "west", "up", "down"],
                "part": ["start", "middle", "end", "single"],
            }
        ),
        "create:mechanical_piston": _entry(
            {"facing": ["north", "east", "south", "west", "up", "down"], "state": ["retracted", "moving", "extended"]}
        ),
        "create:sticky_mechanical_piston": _entry(
            {"facing": ["north", "east", "south", "west", "up", "down"], "state": ["retracted", "moving", "extended"]}
        ),
        "create:sticker": _entry(
            {"extended": ["true", "false"], "facing": ["north", "east", "south", "west", "up", "down"]}
        ),
        "minecraft:piston": _entry(
            {"extended": ["true", "false"], "facing": ["north", "east", "south", "west", "up", "down"]}
        ),
        "minecraft:sticky_piston": _entry(
            {"extended": ["true", "false"], "facing": ["north", "east", "south", "west", "up", "down"]}
        ),
    }
    profile = ServerProfile(
        path=Path("registry.json"),
        format_version=1,
        minecraft_version="1.21.1",
        data_version=3955,
        generated_at=None,
        namespaces={},
        blocks=blocks,
    )

    audit = audit_server_profile(profile)

    assert audit["candidate_count"] == 9
    assert audit["counts_by_status"] == {"validated": 9}
    assert "manual_review" not in audit["counts_by_status"]
