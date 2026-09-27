from pathlib import Path

import pytest

from mcbuild import palette
from mcbuild.global_test_lab import build_registry_lab
from mcbuild.profile import ServerProfile


@pytest.fixture(autouse=True)
def reset_profile():
    palette.configure_server_profile(None)
    yield
    palette.configure_server_profile(None)


def _entry(block_id, properties, states):
    return {
        "namespace": block_id.split(":", 1)[0],
        "path": block_id.split(":", 1)[1],
        "properties": properties,
        "default_state": states[0],
        "states": states,
        "state_count": len(states),
    }


def _simple(block_id):
    return _entry(block_id, {}, [block_id])


def _profile():
    waystone_states = [
        "waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]",
        "waystones:waystone[facing=north,half=upper,origin=player,waterlogged=false]",
    ]
    belt_states = [
        "create:belt[casing=false,facing=east,part=start,slope=horizontal,waterlogged=false]",
        "create:belt[casing=false,facing=east,part=end,slope=horizontal,waterlogged=false]",
    ]
    bed_states = [
        "minecraft:red_bed[facing=east,occupied=false,part=foot]",
        "minecraft:red_bed[facing=east,occupied=false,part=head]",
    ]
    fluid_states = [f"create_dragons_plus:red_dye[level={level}]" for level in range(16)]

    blocks = {
        "minecraft:smooth_stone": _simple("minecraft:smooth_stone"),
        "minecraft:red_bed": _entry(
            "minecraft:red_bed",
            {
                "facing": ["north", "south", "west", "east"],
                "occupied": ["true", "false"],
                "part": ["head", "foot"],
            },
            bed_states,
        ),
        "minecraft:dirt": _simple("minecraft:dirt"),
        "create:andesite_casing": _simple("create:andesite_casing"),
        "create:belt": _entry(
            "create:belt",
            {
                "casing": ["true", "false"],
                "facing": ["north", "south", "west", "east"],
                "part": ["start", "middle", "end", "pulley"],
                "slope": ["horizontal", "upward", "downward", "vertical", "sideways"],
                "waterlogged": ["true", "false"],
            },
            belt_states,
        ),
        "create_dragons_plus:red_dye": _entry(
            "create_dragons_plus:red_dye",
            {"level": [str(level) for level in range(16)]},
            fluid_states,
        ),
        "waystones:waystone": _entry(
            "waystones:waystone",
            {
                "facing": ["north", "south", "west", "east"],
                "half": ["upper", "lower"],
                "origin": ["unknown", "wilderness", "dungeon", "village", "player"],
                "waterlogged": ["true", "false"],
            },
            waystone_states,
        ),
    }

    namespaces = {}
    for block_id in blocks:
        namespace = block_id.split(":", 1)[0]
        namespaces[namespace] = namespaces.get(namespace, 0) + 1

    return ServerProfile(
        path=Path("registry.json"),
        format_version=1,
        minecraft_version="1.21.1",
        data_version=3955,
        generated_at=None,
        namespaces=namespaces,
        blocks=blocks,
    )


def test_default_global_lab_covers_modded_blocks_and_vanilla_fixtures():
    grid, manifest = build_registry_lab(_profile(), columns=4)

    assert len(grid) > 0
    assert manifest["scope"] == "all-modded-plus-vanilla-fixtures"
    assert manifest["tested_by_namespace"] == {
        "create": 2,
        "minecraft": 1,
        "waystones": 1,
    }
    assert manifest["skipped_count"] == 1
    assert manifest["skipped"][0] == {
        "block": "create_dragons_plus:red_dye",
        "reason": "flowing fluid block",
    }

    layout = {entry["block"]: entry for entry in manifest["layout"]}
    assert len(layout["waystones:waystone"]["states"]) == 2
    assert len(layout["create:belt"]["states"]) == 2
    assert len(layout["minecraft:red_bed"]["states"]) == 2


def test_all_blocks_scope_adds_non_fixture_vanilla_blocks():
    _, manifest = build_registry_lab(_profile(), all_blocks=True, columns=4)

    tested = {entry["block"] for entry in manifest["layout"]}
    assert "minecraft:dirt" in tested
    assert manifest["scope"] == "all-registry-blocks"
