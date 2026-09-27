from pathlib import Path

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
        _entry(
            {
                "facing": ["north", "south", "west", "east"],
                "part": ["head", "foot"],
            }
        ),
    )

    assert rules[0]["rule"] == "horizontal_head_foot_pair"
    assert rules[0]["status"] == "validated"


def test_linear_create_part_is_manual_review():
    rules = classify_structure(
        "create:belt",
        _entry(
            {
                "facing": ["north", "south", "west", "east"],
                "part": ["start", "middle", "end", "pulley"],
            }
        ),
    )

    assert rules[0]["rule"] == "linear_multipart"
    assert rules[0]["status"] == "manual_review"


def test_extension_state_is_manual_review():
    rules = classify_structure(
        "minecraft:piston",
        _entry({"extended": ["true", "false"], "facing": ["north", "south"]}),
    )

    assert rules[0]["rule"] == "extension_state"
    assert rules[0]["status"] == "manual_review"


def test_audit_summarizes_supported_and_manual_candidates():
    blocks = {
        "waystones:waystone": _entry({"half": ["upper", "lower"]}),
        "minecraft:red_bed": _entry(
            {"facing": ["north", "south", "west", "east"], "part": ["head", "foot"]}
        ),
        "create:belt": _entry({"part": ["start", "middle", "end", "pulley"]}),
        "minecraft:piston": _entry({"extended": ["true", "false"]}),
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

    assert audit["candidate_count"] == 4
    assert audit["counts_by_status"] == {"manual_review": 2, "validated": 2}
    assert audit["counts_by_rule"] == {
        "extension_state": 1,
        "horizontal_head_foot_pair": 1,
        "linear_multipart": 1,
        "vertical_pair": 1,
    }
