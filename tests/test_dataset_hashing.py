from mcbuild.dataset.hashing import rotate_block_state, rotate_structure, structure_hashes
from mcbuild.dataset.normalize import normalize_structure


def test_directional_block_state_rotation():
    state = "minecraft:oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]"
    assert rotate_block_state(state, 1) == (
        "minecraft:oak_stairs[facing=east,half=bottom,shape=straight,waterlogged=false]"
    )
    assert rotate_block_state("minecraft:oak_log[axis=x]", 1) == "minecraft:oak_log[axis=z]"
    assert rotate_block_state(
        "minecraft:oak_fence[north=true,east=false]",
        1,
    ) == "minecraft:oak_fence[east=true,south=false]"
    assert rotate_block_state(
        "minecraft:rail[shape=ascending_north]",
        1,
    ) == "minecraft:rail[shape=ascending_east]"


def test_rotation_hash_matches_rotated_copy_but_exact_hash_does_not():
    structure = normalize_structure(
        [
            (
                0,
                0,
                0,
                "minecraft:oak_stairs[facing=north,half=bottom,shape=straight]",
            ),
            (1, 0, 0, "minecraft:stone"),
            (1, 1, 0, "minecraft:oak_log[axis=x]"),
        ]
    )
    rotated = rotate_structure(structure, 1)
    original_hashes = structure_hashes(structure)
    rotated_hashes = structure_hashes(rotated)
    assert original_hashes.structure_hash != rotated_hashes.structure_hash
    assert original_hashes.rotation_hash == rotated_hashes.rotation_hash


def test_occupancy_hash_ignores_materials():
    stone = normalize_structure(
        [(0, 0, 0, "stone"), (1, 0, 0, "stone")]
    )
    wool = normalize_structure(
        [(0, 0, 0, "red_wool"), (1, 0, 0, "blue_wool")]
    )
    assert (
        structure_hashes(stone).occupancy_hash
        == structure_hashes(wool).occupancy_hash
    )
    assert (
        structure_hashes(stone).structure_hash
        != structure_hashes(wool).structure_hash
    )
