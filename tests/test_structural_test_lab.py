from pathlib import Path

import pytest

from mcbuild import palette
from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.profile import ServerProfile
from mcbuild.validation import validate_structural_blocks
from mcbuild.voxel import VoxelGrid


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
    blocks = {
        name: _simple(name)
        for name in [
            "minecraft:smooth_stone",
            "minecraft:polished_deepslate",
            "minecraft:blue_concrete",
            "minecraft:red_concrete",
            "minecraft:yellow_concrete",
            "minecraft:orange_concrete",
            "minecraft:lime_concrete",
            "minecraft:cyan_concrete",
            "minecraft:purple_concrete",
            "minecraft:light_blue_concrete",
            "minecraft:white_concrete",
            "minecraft:magenta_concrete",
            "minecraft:redstone_block",
            "create:andesite_casing",
        ]
    }

    blocks["waystones:waystone"] = _entry(
        "waystones:waystone",
        {
            "facing": ["north", "south", "west", "east"],
            "half": ["upper", "lower"],
            "origin": ["unknown", "wilderness", "dungeon", "village", "player"],
            "waterlogged": ["true", "false"],
        },
        [
            "waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]",
            "waystones:waystone[facing=north,half=upper,origin=player,waterlogged=false]",
        ],
    )

    blocks["minecraft:red_bed"] = _entry(
        "minecraft:red_bed",
        {
            "facing": ["north", "south", "west", "east"],
            "occupied": ["true", "false"],
            "part": ["head", "foot"],
        },
        [
            "minecraft:red_bed[facing=east,occupied=false,part=foot]",
            "minecraft:red_bed[facing=east,occupied=false,part=head]",
        ],
    )

    for piston_id in ["minecraft:piston", "minecraft:sticky_piston"]:
        blocks[piston_id] = _entry(
            piston_id,
            {
                "extended": ["true", "false"],
                "facing": ["north", "east", "south", "west", "up", "down"],
            },
            [f"{piston_id}[extended=true,facing=east]"],
        )

    blocks["minecraft:piston_head"] = _entry(
        "minecraft:piston_head",
        {
            "facing": ["north", "east", "south", "west", "up", "down"],
            "short": ["true", "false"],
            "type": ["normal", "sticky"],
        },
        [
            "minecraft:piston_head[facing=east,short=false,type=normal]",
            "minecraft:piston_head[facing=east,short=false,type=sticky]",
        ],
    )

    blocks["create:adjustable_chain_gearshift"] = _entry(
        "create:adjustable_chain_gearshift",
        {
            "axis": ["x", "y", "z"],
            "axis_along_first": ["true", "false"],
            "part": ["start", "middle", "end", "none"],
            "powered": ["true", "false"],
        },
        ["create:adjustable_chain_gearshift[axis=y,axis_along_first=true,part=start,powered=false]"],
    )

    blocks["create:encased_chain_drive"] = _entry(
        "create:encased_chain_drive",
        {
            "axis": ["x", "y", "z"],
            "axis_along_first": ["true", "false"],
            "part": ["start", "middle", "end", "none"],
        },
        [
            "create:encased_chain_drive[axis=y,axis_along_first=true,part=middle]",
            "create:encased_chain_drive[axis=y,axis_along_first=true,part=end]",
        ],
    )

    blocks["create:belt"] = _entry(
        "create:belt",
        {
            "casing": ["true", "false"],
            "facing": ["north", "south", "west", "east"],
            "part": ["start", "middle", "end", "pulley"],
            "slope": ["horizontal", "upward", "downward", "vertical", "sideways"],
            "waterlogged": ["true", "false"],
        },
        [
            "create:belt[casing=false,facing=east,part=start,slope=horizontal,waterlogged=false]",
            "create:belt[casing=false,facing=east,part=middle,slope=horizontal,waterlogged=false]",
            "create:belt[casing=false,facing=east,part=end,slope=horizontal,waterlogged=false]",
            "create:belt[casing=false,facing=east,part=start,slope=upward,waterlogged=false]",
            "create:belt[casing=false,facing=east,part=middle,slope=upward,waterlogged=false]",
            "create:belt[casing=false,facing=east,part=end,slope=upward,waterlogged=false]",
        ],
    )

    blocks["create:gantry_shaft"] = _entry(
        "create:gantry_shaft",
        {
            "facing": ["north", "east", "south", "west", "up", "down"],
            "part": ["start", "middle", "end", "single"],
            "powered": ["true", "false"],
        },
        [
            "create:gantry_shaft[facing=east,part=start,powered=false]",
            "create:gantry_shaft[facing=east,part=middle,powered=false]",
            "create:gantry_shaft[facing=east,part=end,powered=false]",
        ],
    )

    blocks["create:sticker"] = _entry(
        "create:sticker",
        {
            "extended": ["true", "false"],
            "facing": ["north", "east", "south", "west", "up", "down"],
            "powered": ["true", "false"],
        },
        ["create:sticker[extended=true,facing=east,powered=true]"],
    )

    for piston_id in ["create:mechanical_piston", "create:sticky_mechanical_piston"]:
        blocks[piston_id] = _entry(
            piston_id,
            {
                "axis_along_first": ["true", "false"],
                "facing": ["north", "east", "south", "west", "up", "down"],
                "state": ["retracted", "moving", "extended"],
            },
            [f"{piston_id}[axis_along_first=true,facing=east,state=extended]"],
        )

    blocks["create:piston_extension_pole"] = _entry(
        "create:piston_extension_pole",
        {
            "facing": ["north", "east", "south", "west", "up", "down"],
            "waterlogged": ["true", "false"],
        },
        ["create:piston_extension_pole[facing=east,waterlogged=false]"],
    )

    blocks["create:mechanical_piston_head"] = _entry(
        "create:mechanical_piston_head",
        {
            "facing": ["north", "east", "south", "west", "up", "down"],
            "type": ["normal", "sticky"],
            "waterlogged": ["true", "false"],
        },
        [
            "create:mechanical_piston_head[facing=east,type=normal,waterlogged=false]",
            "create:mechanical_piston_head[facing=east,type=sticky,waterlogged=false]",
        ],
    )

    namespaces = {}
    for block_id in blocks:
        namespace = block_id.split(":", 1)[0]
        namespaces[namespace] = namespaces.get(namespace, 0) + 1

    return ServerProfile(
        path=Path("test-structural-profile.json"),
        format_version=1,
        minecraft_version="1.21.1",
        data_version=3955,
        generated_at=None,
        namespaces=namespaces,
        blocks=blocks,
    )


def test_structural_test_lab_blueprint_executes_and_validates():
    palette.configure_server_profile(_profile())
    source = Path("blueprints/02-structural-test-lab.py").read_text(encoding="utf-8")
    grid = VoxelGrid()

    run_blueprint(source, grid, seed=0)
    validate_structural_blocks(grid)

    assert len(grid) > 800
    assert grid.bounds is not None
