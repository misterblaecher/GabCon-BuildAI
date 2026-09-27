import json

import pytest

from mcbuild import palette
from mcbuild.profile import ServerProfile
from mcbuild.validation import BuildValidationError, validate_double_height_blocks
from mcbuild.voxel import VoxelGrid


@pytest.fixture(autouse=True)
def reset_profile():
    palette.configure_server_profile(None)
    yield
    palette.configure_server_profile(None)


def _waystone_profile(tmp_path):
    states = []
    for half in ("lower", "upper"):
        states.append(f"waystones:waystone[facing=north,half={half},origin=player,waterlogged=false]")
    payload = {
        "format_version": 1,
        "minecraft_version": "1.21.1",
        "data_version": 3955,
        "generated_at": "2026-09-27T10:20:55Z",
        "block_count": 1,
        "state_count": 2,
        "namespaces": {"waystones": 1},
        "blocks": {
            "waystones:waystone": {
                "namespace": "waystones",
                "path": "waystone",
                "properties": {
                    "facing": ["north"],
                    "half": ["upper", "lower"],
                    "origin": ["player"],
                    "waterlogged": ["false"],
                },
                "default_state": states[0],
                "states": states,
                "state_count": 2,
            }
        },
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return ServerProfile.load(path)


def test_orphaned_waystone_lower_half_is_rejected(tmp_path):
    palette.configure_server_profile(_waystone_profile(tmp_path))
    grid = VoxelGrid()
    lower = palette.get_block("waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]")
    grid.set(2, 1, 4, lower.index)

    with pytest.raises(BuildValidationError, match="upper half is missing"):
        validate_double_height_blocks(grid)


def test_bare_waystone_uses_default_lower_half_for_validation(tmp_path):
    palette.configure_server_profile(_waystone_profile(tmp_path))
    grid = VoxelGrid()
    grid.set(2, 1, 4, palette.get_block("waystones:waystone").index)

    with pytest.raises(BuildValidationError, match="upper half is missing"):
        validate_double_height_blocks(grid)


def test_complete_waystone_pair_passes(tmp_path):
    palette.configure_server_profile(_waystone_profile(tmp_path))
    grid = VoxelGrid()
    lower = palette.get_block("waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]")
    upper = palette.get_block("waystones:waystone[facing=north,half=upper,origin=player,waterlogged=false]")
    grid.set(2, 1, 4, lower.index)
    grid.set(2, 2, 4, upper.index)

    validate_double_height_blocks(grid)
