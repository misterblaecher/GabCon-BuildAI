from pathlib import Path

import pytest

from mcbuild import palette
from mcbuild.profile import ServerProfile
from mcbuild.validation import BuildValidationError, validate_structural_blocks
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


def _profile(blocks):
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


def _set(grid, x, y, z, block_id):
    grid.set(x, y, z, palette.get_block(block_id).index)


def test_create_chain_drive_pair_passes():
    blocks = {
        "create:adjustable_chain_gearshift": _entry(
            "create:adjustable_chain_gearshift",
            {
                "axis": ["y"],
                "axis_along_first": ["true"],
                "part": ["start", "middle", "end", "none"],
                "powered": ["false"],
            },
            ["create:adjustable_chain_gearshift[axis=y,axis_along_first=true,part=start,powered=false]"],
        ),
        "create:encased_chain_drive": _entry(
            "create:encased_chain_drive",
            {"axis": ["y"], "axis_along_first": ["true"], "part": ["end"]},
            ["create:encased_chain_drive[axis=y,axis_along_first=true,part=end]"],
        ),
    }
    palette.configure_server_profile(_profile(blocks))
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, blocks["create:adjustable_chain_gearshift"]["states"][0])
    _set(grid, 1, 0, 0, blocks["create:encased_chain_drive"]["states"][0])

    validate_structural_blocks(grid)


def test_create_chain_drive_missing_neighbor_is_rejected():
    block_id = "create:encased_chain_drive"
    state = "create:encased_chain_drive[axis=y,axis_along_first=true,part=start]"
    palette.configure_server_profile(
        _profile(
            {
                block_id: _entry(
                    block_id,
                    {"axis": ["y"], "axis_along_first": ["true"], "part": ["start"]},
                    [state],
                )
            }
        )
    )
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, state)

    with pytest.raises(BuildValidationError, match="chain-drive neighbors"):
        validate_structural_blocks(grid)


def test_create_gantry_start_end_pair_passes():
    block_id = "create:gantry_shaft"
    start = "create:gantry_shaft[facing=east,part=start,powered=false]"
    end = "create:gantry_shaft[facing=east,part=end,powered=false]"
    palette.configure_server_profile(
        _profile(
            {
                block_id: _entry(
                    block_id,
                    {
                        "facing": ["east"],
                        "part": ["start", "middle", "end", "single"],
                        "powered": ["false"],
                    },
                    [start, end],
                )
            }
        )
    )
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, start)
    _set(grid, 1, 0, 0, end)

    validate_structural_blocks(grid)


def test_create_belt_upward_pair_passes():
    block_id = "create:belt"
    start = "create:belt[casing=false,facing=east,part=start,slope=upward,waterlogged=false]"
    end = "create:belt[casing=false,facing=east,part=end,slope=upward,waterlogged=false]"
    palette.configure_server_profile(
        _profile(
            {
                block_id: _entry(
                    block_id,
                    {
                        "casing": ["false"],
                        "facing": ["east"],
                        "part": ["start", "middle", "end", "single"],
                        "slope": ["upward"],
                        "waterlogged": ["false"],
                    },
                    [start, end],
                )
            }
        )
    )
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, start)
    _set(grid, 1, 1, 0, end)

    validate_structural_blocks(grid)


def test_create_belt_missing_end_is_rejected():
    block_id = "create:belt"
    start = "create:belt[casing=false,facing=east,part=start,slope=horizontal,waterlogged=false]"
    palette.configure_server_profile(
        _profile(
            {
                block_id: _entry(
                    block_id,
                    {
                        "casing": ["false"],
                        "facing": ["east"],
                        "part": ["start", "middle", "end", "none"],
                        "slope": ["horizontal"],
                        "waterlogged": ["false"],
                    },
                    [start],
                )
            }
        )
    )
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, start)

    with pytest.raises(BuildValidationError, match="missing its next belt segment"):
        validate_structural_blocks(grid)


def test_create_sticker_extended_needs_no_companion_block():
    block_id = "create:sticker"
    state = "create:sticker[extended=true,facing=north,powered=true]"
    palette.configure_server_profile(
        _profile(
            {
                block_id: _entry(
                    block_id,
                    {
                        "extended": ["true", "false"],
                        "facing": ["north"],
                        "powered": ["true"],
                    },
                    [state],
                )
            }
        )
    )
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, state)

    validate_structural_blocks(grid)


def test_vanilla_extended_piston_requires_matching_head():
    piston = "minecraft:piston[extended=true,facing=east]"
    head = "minecraft:piston_head[facing=east,short=false,type=normal]"
    blocks = {
        "minecraft:piston": _entry(
            "minecraft:piston",
            {"extended": ["true", "false"], "facing": ["east"]},
            [piston],
        ),
        "minecraft:piston_head": _entry(
            "minecraft:piston_head",
            {"facing": ["east"], "short": ["false"], "type": ["normal"]},
            [head],
        ),
    }
    palette.configure_server_profile(_profile(blocks))
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, piston)
    _set(grid, 1, 0, 0, head)

    validate_structural_blocks(grid)


def test_sticky_piston_rejects_normal_head():
    piston = "minecraft:sticky_piston[extended=true,facing=east]"
    head = "minecraft:piston_head[facing=east,short=false,type=normal]"
    blocks = {
        "minecraft:sticky_piston": _entry(
            "minecraft:sticky_piston",
            {"extended": ["true", "false"], "facing": ["east"]},
            [piston],
        ),
        "minecraft:piston_head": _entry(
            "minecraft:piston_head",
            {"facing": ["east"], "short": ["false"], "type": ["normal"]},
            [head],
        ),
    }
    palette.configure_server_profile(_profile(blocks))
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, piston)
    _set(grid, 1, 0, 0, head)

    with pytest.raises(BuildValidationError, match="type=sticky"):
        validate_structural_blocks(grid)


def test_create_extended_mechanical_piston_with_pole_and_head_passes():
    piston = "create:mechanical_piston[axis_along_first=true,facing=east,state=extended]"
    pole = "create:piston_extension_pole[facing=east,waterlogged=false]"
    head = "create:mechanical_piston_head[facing=east,type=normal,waterlogged=false]"
    blocks = {
        "create:mechanical_piston": _entry(
            "create:mechanical_piston",
            {
                "axis_along_first": ["true"],
                "facing": ["east"],
                "state": ["retracted", "moving", "extended"],
            },
            [piston],
        ),
        "create:piston_extension_pole": _entry(
            "create:piston_extension_pole",
            {"facing": ["east"], "waterlogged": ["false"]},
            [pole],
        ),
        "create:mechanical_piston_head": _entry(
            "create:mechanical_piston_head",
            {"facing": ["east"], "type": ["normal"], "waterlogged": ["false"]},
            [head],
        ),
    }
    palette.configure_server_profile(_profile(blocks))
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, piston)
    _set(grid, 1, 0, 0, pole)
    _set(grid, 2, 0, 0, head)

    validate_structural_blocks(grid)


def test_create_mechanical_piston_moving_state_is_rejected():
    piston = "create:mechanical_piston[axis_along_first=true,facing=east,state=moving]"
    palette.configure_server_profile(
        _profile(
            {
                "create:mechanical_piston": _entry(
                    "create:mechanical_piston",
                    {
                        "axis_along_first": ["true"],
                        "facing": ["east"],
                        "state": ["retracted", "moving", "extended"],
                    },
                    [piston],
                )
            }
        )
    )
    grid = VoxelGrid()
    _set(grid, 0, 0, 0, piston)

    with pytest.raises(BuildValidationError, match="transient state=moving"):
        validate_structural_blocks(grid)
