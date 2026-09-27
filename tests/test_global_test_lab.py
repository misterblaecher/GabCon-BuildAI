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
    grid, support_grid, manifest = build_registry_lab(_profile(), columns=4)

    assert len(grid) > 0
    assert len(support_grid) > 0
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
    _, _, manifest = build_registry_lab(_profile(), all_blocks=True, columns=4)

    tested = {entry["block"] for entry in manifest["layout"]}
    assert "minecraft:dirt" in tested
    assert manifest["scope"] == "all-registry-blocks"


def _reported_failures_profile():
    belt_states = [
        f"create:belt[casing={casing},facing=east,part={part},slope=horizontal,waterlogged=false]"
        for casing in ("false", "true")
        for part in ("start", "middle", "end")
    ]
    blocks = {
        "minecraft:smooth_stone": _simple("minecraft:smooth_stone"),
        "minecraft:dirt": _simple("minecraft:dirt"),
        "minecraft:soul_sand": _simple("minecraft:soul_sand"),
        "minecraft:crimson_nylium": _simple("minecraft:crimson_nylium"),
        "minecraft:warped_nylium": _simple("minecraft:warped_nylium"),
        "minecraft:mycelium": _simple("minecraft:mycelium"),
        "minecraft:farmland": _entry(
            "minecraft:farmland",
            {"moisture": [str(value) for value in range(8)]},
            [f"minecraft:farmland[moisture={value}]" for value in range(8)],
        ),
        "minecraft:water": _entry(
            "minecraft:water",
            {"level": [str(value) for value in range(16)]},
            [f"minecraft:water[level={value}]" for value in range(16)],
        ),
        "minecraft:cave_air": _simple("minecraft:cave_air"),
        "minecraft:rail": _entry(
            "minecraft:rail",
            {
                "shape": [
                    "north_south",
                    "east_west",
                    "ascending_east",
                    "ascending_west",
                    "ascending_north",
                    "ascending_south",
                    "south_east",
                    "south_west",
                    "north_west",
                    "north_east",
                ],
                "waterlogged": ["true", "false"],
            },
            [
                "minecraft:rail[shape=ascending_east,waterlogged=false]",
                "minecraft:rail[shape=north_south,waterlogged=false]",
            ],
        ),
        "minecraft:powered_rail": _entry(
            "minecraft:powered_rail",
            {
                "powered": ["true", "false"],
                "shape": [
                    "north_south",
                    "east_west",
                    "ascending_east",
                    "ascending_west",
                    "ascending_north",
                    "ascending_south",
                ],
                "waterlogged": ["true", "false"],
            },
            [
                "minecraft:powered_rail[powered=false,shape=ascending_east,waterlogged=false]",
                "minecraft:powered_rail[powered=false,shape=north_south,waterlogged=false]",
            ],
        ),
        "create:controller_rail": _entry(
            "create:controller_rail",
            {
                "backwards": ["true", "false"],
                "power": [str(value) for value in range(16)],
                "shape": [
                    "north_south",
                    "east_west",
                    "ascending_east",
                    "ascending_west",
                    "ascending_north",
                    "ascending_south",
                ],
                "waterlogged": ["true", "false"],
            },
            [
                "create:controller_rail[backwards=false,power=0,shape=ascending_east,waterlogged=false]",
                "create:controller_rail[backwards=false,power=0,shape=north_south,waterlogged=false]",
            ],
        ),
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
        "create:gantry_shaft": _entry(
            "create:gantry_shaft",
            {
                "facing": ["north", "east", "south", "west", "up", "down"],
                "part": ["start", "middle", "end", "single"],
                "powered": ["true", "false"],
            },
            ["create:gantry_shaft[facing=east,part=single,powered=false]"],
        ),
        "create:gantry_carriage": _entry(
            "create:gantry_carriage",
            {
                "axis_along_first": ["true", "false"],
                "facing": ["north", "east", "south", "west", "up", "down"],
            },
            ["create:gantry_carriage[axis_along_first=false,facing=up]"],
        ),
        "create:encased_fan": _entry(
            "create:encased_fan",
            {"facing": ["north", "east", "south", "west", "up", "down"]},
            ["create:encased_fan[facing=up]"],
        ),
        "create:nozzle": _entry(
            "create:nozzle",
            {"facing": ["north", "east", "south", "west", "up", "down"]},
            ["create:nozzle[facing=up]"],
        ),
        "create:redstone_link": _entry(
            "create:redstone_link",
            {
                "facing": ["north", "east", "south", "west", "up", "down"],
                "powered": ["true", "false"],
                "receiver": ["true", "false"],
            },
            ["create:redstone_link[facing=up,powered=false,receiver=false]"],
        ),
        "create:peculiar_bell": _entry(
            "create:peculiar_bell",
            {
                "attachment": ["floor", "ceiling", "single_wall", "double_wall"],
                "facing": ["north", "south", "west", "east"],
                "powered": ["true", "false"],
            },
            [
                "create:peculiar_bell[attachment=ceiling,facing=north,powered=false]",
                "create:peculiar_bell[attachment=floor,facing=north,powered=false]",
            ],
        ),
        "create:andesite_tunnel": _entry(
            "create:andesite_tunnel",
            {
                "axis": ["x", "z"],
                "shape": ["straight", "window", "closed", "t_left", "t_right", "cross"],
            },
            ["create:andesite_tunnel[axis=x,shape=straight]"],
        ),
        "create:brass_tunnel": _entry(
            "create:brass_tunnel",
            {
                "axis": ["x", "z"],
                "shape": ["straight", "window", "closed", "t_left", "t_right", "cross"],
            },
            ["create:brass_tunnel[axis=x,shape=straight]"],
        ),
        "create:hand_crank": _entry(
            "create:hand_crank",
            {
                "facing": ["north", "east", "south", "west", "up", "down"],
                "waterlogged": ["true", "false"],
            },
            ["create:hand_crank[facing=up,waterlogged=false]"],
        ),
        "create:green_valve_handle": _entry(
            "create:green_valve_handle",
            {
                "facing": ["north", "east", "south", "west", "up", "down"],
                "waterlogged": ["true", "false"],
            },
            ["create:green_valve_handle[facing=up,waterlogged=false]"],
        ),
        "create:haunted_bell": _entry(
            "create:haunted_bell",
            {
                "attachment": ["floor", "ceiling", "single_wall", "double_wall"],
                "facing": ["north", "south", "west", "east"],
                "powered": ["true", "false"],
            },
            [
                "create:haunted_bell[attachment=ceiling,facing=north,powered=false]",
                "create:haunted_bell[attachment=floor,facing=north,powered=false]",
            ],
        ),
        "create:fluid_tank": _entry(
            "create:fluid_tank",
            {
                "bottom": ["true", "false"],
                "shape": ["plain", "window", "window_nw", "window_sw", "window_ne", "window_se"],
                "top": ["true", "false"],
            },
            ["create:fluid_tank[bottom=true,shape=window,top=true]"],
        ),
        "create:steam_whistle": _entry(
            "create:steam_whistle",
            {
                "facing": ["north", "south", "west", "east"],
                "powered": ["true", "false"],
                "size": ["small", "medium", "large"],
                "wall": ["true", "false"],
            },
            ["create:steam_whistle[facing=north,powered=false,size=medium,wall=false]"],
        ),
        "minecraft:dandelion": _simple("minecraft:dandelion"),
        "minecraft:wheat": _entry(
            "minecraft:wheat",
            {"age": [str(value) for value in range(8)]},
            [f"minecraft:wheat[age={value}]" for value in range(8)],
        ),
        "minecraft:crimson_fungus": _simple("minecraft:crimson_fungus"),
        "minecraft:warped_roots": _simple("minecraft:warped_roots"),
        "minecraft:red_mushroom": _simple("minecraft:red_mushroom"),
        "minecraft:nether_wart": _entry(
            "minecraft:nether_wart",
            {"age": ["0", "1", "2", "3"]},
            [f"minecraft:nether_wart[age={value}]" for value in range(4)],
        ),
        "minecraft:lily_pad": _simple("minecraft:lily_pad"),
        "minecraft:spore_blossom": _simple("minecraft:spore_blossom"),
        "minecraft:tripwire_hook": _entry(
            "minecraft:tripwire_hook",
            {
                "attached": ["true", "false"],
                "facing": ["north", "south", "west", "east"],
                "powered": ["true", "false"],
            },
            ["minecraft:tripwire_hook[attached=false,facing=north,powered=false]"],
        ),
        "waystones:warp_plate": _entry(
            "waystones:warp_plate",
            {
                "facing": ["north", "south", "west", "east"],
                "origin": ["unknown", "wilderness", "dungeon", "village", "player"],
                "status": ["empty", "idle", "attuning", "warping", "warping_invalid", "redstone_disabled", "locked"],
                "waterlogged": ["true", "false"],
            },
            [
                "waystones:warp_plate[facing=north,origin=dungeon,status=attuning,waterlogged=false]",
                "waystones:warp_plate[facing=north,origin=player,status=empty,waterlogged=false]",
            ],
        ),
    }

    namespaces = {}
    for block_id in blocks:
        namespace = block_id.split(":", 1)[0]
        namespaces[namespace] = namespaces.get(namespace, 0) + 1

    return ServerProfile(
        path=Path("reported-failures-registry.json"),
        format_version=1,
        minecraft_version="1.21.1",
        data_version=3955,
        generated_at=None,
        namespaces=namespaces,
        blocks=blocks,
    )


def test_reported_fragile_blocks_get_survival_safe_fixtures():
    _, support_grid, manifest = build_registry_lab(_reported_failures_profile(), columns=8)
    layout = {entry["block"]: entry for entry in manifest["layout"]}

    assert "facing=up" in layout["create:hand_crank"]["states"][0]["state"]
    assert "facing=up" in layout["create:green_valve_handle"]["states"][0]["state"]
    assert "attachment=floor" in layout["create:haunted_bell"]["states"][0]["state"]
    assert "attachment=floor" in layout["create:peculiar_bell"]["states"][0]["state"]
    assert "facing=up" in layout["create:redstone_link"]["states"][0]["state"]
    assert "shape=north_south" in layout["create:controller_rail"]["states"][0]["state"]

    carriage_states = layout["create:gantry_carriage"]["states"]
    assert carriage_states[0]["state"] == "create:gantry_shaft[facing=east,part=single,powered=false]"
    assert carriage_states[0]["fixture"] is True
    assert carriage_states[1]["state"] == "create:gantry_carriage[axis_along_first=false,facing=up]"

    nozzle_states = layout["create:nozzle"]["states"]
    assert nozzle_states[0]["state"] == "create:encased_fan[facing=up]"
    assert nozzle_states[0]["fixture"] is True
    assert nozzle_states[1]["state"] == "create:nozzle[facing=up]"

    andesite_states = layout["create:andesite_tunnel"]["states"]
    brass_states = layout["create:brass_tunnel"]["states"]
    assert len(andesite_states) == 4
    assert len(brass_states) == 4
    assert sum(state["fixture"] for state in andesite_states) == 3
    assert any("create:belt[casing=true" in state["state"] for state in andesite_states)

    whistle_states = layout["create:steam_whistle"]["states"]
    assert len(whistle_states) == 2
    assert whistle_states[0]["state"] == "create:fluid_tank[bottom=true,shape=window,top=true]"
    assert whistle_states[0]["fixture"] is True
    assert whistle_states[1]["state"] == "create:steam_whistle[facing=north,powered=false,size=medium,wall=false]"

    support_ids = {palette.get_block_by_index(idx).base_id for _, idx in support_grid.items()}
    assert "create:gantry_shaft" in support_ids
    assert "create:encased_fan" in support_ids
    assert "create:fluid_tank" in support_ids
    assert "create:belt" in support_ids

    assert "shape=north_south" in layout["minecraft:rail"]["states"][0]["state"]
    assert "shape=north_south" in layout["minecraft:powered_rail"]["states"][0]["state"]
    assert "powered=false" in layout["minecraft:powered_rail"]["states"][0]["state"]

    warp_plate = layout["waystones:warp_plate"]
    assert "origin=player" in warp_plate["states"][0]["state"]
    assert "status=empty" in warp_plate["states"][0]["state"]
    assert warp_plate["expected_side_effect"] is not None


def test_all_blocks_uses_survival_substrates_for_fragile_vanilla_blocks():
    _, support_grid, manifest = build_registry_lab(_reported_failures_profile(), all_blocks=True, columns=8)
    layout = {entry["block"]: entry for entry in manifest["layout"]}

    assert layout["minecraft:dandelion"]["states"][0]["base_support"] == "minecraft:dirt"
    assert layout["minecraft:wheat"]["states"][0]["base_support"] == "minecraft:farmland[moisture=7]"
    assert layout["minecraft:crimson_fungus"]["states"][0]["base_support"] == "minecraft:crimson_nylium"
    assert layout["minecraft:warped_roots"]["states"][0]["base_support"] == "minecraft:warped_nylium"
    assert layout["minecraft:red_mushroom"]["states"][0]["base_support"] == "minecraft:mycelium"
    assert layout["minecraft:nether_wart"]["states"][0]["base_support"] == "minecraft:soul_sand"
    assert layout["minecraft:lily_pad"]["states"][0]["base_support"] == "minecraft:water[level=0]"

    support_ids = {palette.get_block_by_index(idx).base_id for _, idx in support_grid.items()}
    assert "minecraft:water" in support_ids


def test_all_blocks_skips_palette_excluded_air_variants():
    _, _, manifest = build_registry_lab(_reported_failures_profile(), all_blocks=True, columns=8)

    skipped = {entry["block"]: entry["reason"] for entry in manifest["skipped"]}
    assert skipped["minecraft:cave_air"] == "air-like block"
