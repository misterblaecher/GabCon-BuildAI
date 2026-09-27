import json

import pytest

from mcbuild import palette
from mcbuild.profile import ProfileError, ServerProfile


@pytest.fixture(autouse=True)
def reset_palette_profile():
    palette.configure_server_profile(None)
    yield
    palette.configure_server_profile(None)


def _write_registry(tmp_path):
    payload = {
        "format_version": 1,
        "minecraft_version": "1.21.1",
        "data_version": 3955,
        "generated_at": "2026-09-27T10:20:55Z",
        "block_count": 2,
        "state_count": 5,
        "namespaces": {"create": 1, "minecraft": 1},
        "blocks": {
            "create:andesite_casing": {
                "namespace": "create",
                "path": "andesite_casing",
                "properties": {},
                "default_state": "create:andesite_casing",
                "states": ["create:andesite_casing"],
                "state_count": 1,
            },
            "minecraft:oak_slab": {
                "namespace": "minecraft",
                "path": "oak_slab",
                "properties": {
                    "type": ["top", "bottom"],
                    "waterlogged": ["true", "false"],
                },
                "default_state": "minecraft:oak_slab[type=bottom,waterlogged=false]",
                "states": [
                    "minecraft:oak_slab[type=bottom,waterlogged=false]",
                    "minecraft:oak_slab[type=bottom,waterlogged=true]",
                    "minecraft:oak_slab[type=top,waterlogged=false]",
                    "minecraft:oak_slab[type=top,waterlogged=true]",
                ],
                "state_count": 4,
            },
        },
    }
    path = tmp_path / "server-block-registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_profile_loads_and_configures_modded_ids(tmp_path):
    path = _write_registry(tmp_path)
    profile = palette.configure_server_registry(path)

    assert profile.minecraft_version == "1.21.1"
    assert profile.data_version == 3955
    assert palette.get_block("create:andesite_casing").mc_id == "create:andesite_casing"
    assert "create:andesite_casing" in palette.all_block_ids()


def test_partial_state_is_valid_when_matching_exported_state(tmp_path):
    palette.configure_server_registry(_write_registry(tmp_path))

    block = palette.get_block("oak_slab[type=top]")
    assert block.mc_id == "minecraft:oak_slab[type=top]"


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("oak_slab[half=top]", "Invalid state property"),
        ("oak_slab[type=side]", "Invalid value"),
    ],
)
def test_invalid_state_property_or_value_is_rejected(tmp_path, name, message):
    palette.configure_server_registry(_write_registry(tmp_path))

    with pytest.raises(palette.PaletteError, match=message):
        palette.get_block(name)


def test_invalid_profile_counts_are_rejected(tmp_path):
    path = _write_registry(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["block_count"] = 999
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ProfileError, match="block_count"):
        ServerProfile.load(path)


def test_registry_metadata_does_not_expose_local_path(tmp_path):
    palette.configure_server_registry(_write_registry(tmp_path))

    metadata = palette.registry_metadata()
    assert metadata["source"] == "server-export"
    assert metadata["minecraft_version"] == "1.21.1"
    assert metadata["data_version"] == 3955
    assert "path" not in metadata
