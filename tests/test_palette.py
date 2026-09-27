import pytest

from mcbuild.palette import (
    PaletteError,
    _canonical_base_id,
    _mc_id,
    all_block_ids,
    get_block,
    pop_warnings,
    reset_warnings,
    suggest,
)


def test_get_known_block():
    block = get_block("oak_planks")
    assert block.namespace == "minecraft"
    assert block.name == "oak_planks"
    assert block.base_id == "minecraft:oak_planks"
    assert block.mc_id == "minecraft:oak_planks"
    assert block.rgb == (162, 130, 78)


def test_get_block_with_minecraft_prefix():
    block = get_block("minecraft:stone")
    assert block.name == "stone"


def test_unknown_block_raises_with_suggestion():
    with pytest.raises(PaletteError) as exc_info:
        get_block("totally_bogus_block_xyz")
    assert "Unknown block" in str(exc_info.value)


def test_near_miss_typo_auto_corrects_with_warning():
    reset_warnings()
    block = get_block("oak_plank")  # missing 's' — close enough to auto-correct
    assert block.mc_id == "minecraft:oak_planks"
    warnings = pop_warnings()
    assert any("oak_plank" in w and "oak_planks" in w for w in warnings)


def test_suggest_returns_close_matches():
    matches = suggest("stoen")
    assert "stone" in matches


def test_air_is_valid_and_non_renderable():
    block = get_block("air")
    assert block.mc_id == "minecraft:air"
    assert block.renderable is False


def test_cave_air_still_excluded():
    with pytest.raises(PaletteError):
        get_block("cave_air")


def test_registry_is_canonicalized_to_namespaced_ids():
    ids = all_block_ids()
    assert "minecraft:stone" in ids
    assert "stone" not in ids


def test_namespaced_mod_id_is_preserved():
    base_id = _canonical_base_id("create:andesite_casing")
    assert base_id == "create:andesite_casing"
    assert _mc_id(base_id, (("axis", "y"),)) == "create:andesite_casing[axis=y]"


def test_unqualified_id_defaults_to_minecraft_namespace():
    assert _canonical_base_id("stone_bricks") == "minecraft:stone_bricks"


def test_suggestions_do_not_cross_namespaces():
    # Until a Create registry is loaded, a Create typo must not silently turn
    # into a similarly named vanilla block.
    assert suggest("create:stone") == []
