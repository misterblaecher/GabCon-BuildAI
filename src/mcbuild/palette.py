"""Block palette: namespaced block IDs validated against the configured block registry.

Colors come from a curated hand-picked table where available, otherwise are
derived lazily from the real block texture (averaging its opaque pixels), and
finally fall back to a neutral gray if neither exists.

v1's voxel model and renderer only understand full 1x1x1 cubes, so blocks with
sub-block shapes (stairs, slabs, doors, ...) are still *valid names* here (the
registry doesn't distinguish shape), but will be placed/rendered as a plain
cube rather than their true geometry — noted as a v2 improvement.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path

from mcbuild.profile import ServerProfile

REGISTRY_PATH = Path(__file__).resolve().parent / "assets" / "minecraft_block_registry.json"

# Present in the registry but not meaningfully placeable as a build voxel.
# Note: plain "air" IS allowed — it's a useful carve/erase block (renders as empty
# space, exports as minecraft:air to actively clear terrain on paste). The remaining
# entries are obscure technical variants with no build use.
_EXCLUDED_NAMES = {"cave_air", "void_air", "structure_void"}

# Common non-canonical / renamed block names an LLM might emit, mapped to the
# registry's actual name. Consulted in get_block() before the registry lookup fails.
ALIAS: dict[str, str] = {
    "grass": "short_grass",
    "redstone_repeater": "repeater",
    "redstone_comparator": "comparator",
    "glow_berries": "cave_vines",
    "iron_chain": "chain",  # 1.21.9-era name; registry/exports target 1.21.1's "chain"
    "sign": "oak_sign",
    "wall_sign": "oak_wall_sign",
    "stone_slab": "smooth_stone_slab",
    "grass_path": "dirt_path",
}

# Non-fatal palette warnings collected during a single blueprint execution (aliasing,
# confident fuzzy-match auto-correction). Reset at the start of each sandbox run and
# flushed onto the grid after a successful build.
_warnings: list[str] = []


def reset_warnings() -> None:
    _warnings.clear()


def pop_warnings() -> list[str]:
    out = list(_warnings)
    _warnings.clear()
    return out


@dataclass(frozen=True)
class Block:
    """A single palette entry.

    `namespace` and `name` identify the base block (e.g. `minecraft` + `oak_stairs`);
    `state` holds parsed block-state props as sorted (key, value) pairs, and `mc_id`
    contains the canonical namespaced ID plus the optional `[state]` suffix for export.
    `renderable` is False only when no
    color/texture can be resolved even from the base material (e.g. air) — such blocks are
    still placed/exported but skipped by the preview renderer.
    """

    index: int
    namespace: str  # e.g. "minecraft" or "create"
    name: str  # namespace-local path, e.g. "oak_stairs" or "andesite_casing"
    mc_id: str  # e.g. "minecraft:oak_stairs[facing=north,half=top]"
    rgb: tuple[int, int, int]
    transparent: bool = False
    renderable: bool = True
    state: tuple[tuple[str, str], ...] = ()

    @property
    def base_id(self) -> str:
        """Canonical namespaced block ID without block-state properties."""
        return f"{self.namespace}:{self.name}"


class PaletteError(Exception):
    """Raised when a blueprint references an unknown block name."""


# name -> (rgb, transparent). Curated by hand for common/visually important blocks;
# every other registry block is resolved lazily from its texture (see _resolve).
_CURATED: dict[str, tuple[tuple[int, int, int], bool]] = {
    # --- Stone family ---
    "stone": ((125, 125, 125), False),
    "cobblestone": ((122, 122, 122), False),
    "mossy_cobblestone": ((110, 122, 100), False),
    "stone_bricks": ((122, 122, 122), False),
    "mossy_stone_bricks": ((115, 120, 105), False),
    "cracked_stone_bricks": ((117, 117, 117), False),
    "chiseled_stone_bricks": ((120, 120, 120), False),
    "smooth_stone": ((160, 160, 160), False),
    "granite": ((149, 103, 85), False),
    "polished_granite": ((152, 108, 91), False),
    "diorite": ((188, 188, 188), False),
    "polished_diorite": ((196, 196, 199), False),
    "andesite": ((132, 133, 132), False),
    "polished_andesite": ((131, 137, 133), False),
    "bedrock": ((85, 85, 85), False),
    "gravel": ((132, 128, 124), False),
    "obsidian": ((20, 18, 29), False),
    "crying_obsidian": ((32, 10, 63), False),
    # --- Deepslate family ---
    "deepslate": ((78, 78, 84), False),
    "cobbled_deepslate": ((76, 76, 79), False),
    "polished_deepslate": ((70, 70, 75), False),
    "deepslate_bricks": ((65, 65, 70), False),
    "deepslate_tiles": ((62, 62, 66), False),
    "chiseled_deepslate": ((68, 68, 72), False),
    "cracked_deepslate_bricks": ((63, 63, 67), False),
    "cracked_deepslate_tiles": ((60, 60, 64), False),
    # --- Brick / sandstone / quartz ---
    "bricks": ((150, 97, 83), False),
    "mud_bricks": ((140, 105, 78), False),
    "sandstone": ((216, 203, 155), False),
    "chiseled_sandstone": ((214, 201, 154), False),
    "cut_sandstone": ((216, 204, 158), False),
    "smooth_sandstone": ((219, 207, 163), False),
    "red_sandstone": ((181, 99, 32), False),
    "chiseled_red_sandstone": ((179, 97, 31), False),
    "cut_red_sandstone": ((181, 100, 33), False),
    "smooth_red_sandstone": ((183, 101, 34), False),
    "quartz_block": ((235, 229, 222), False),
    "smooth_quartz": ((237, 233, 226), False),
    "chiseled_quartz_block": ((233, 229, 224), False),
    "quartz_pillar": ((231, 226, 219), False),
    "quartz_bricks": ((234, 228, 221), False),
    "purpur_block": ((169, 125, 169), False),
    "purpur_pillar": ((171, 127, 171), False),
    "prismarine": ((99, 156, 151), False),
    "prismarine_bricks": ((99, 172, 153), False),
    "dark_prismarine": ((68, 99, 78), False),
    "nether_bricks": ((44, 22, 26), False),
    "red_nether_bricks": ((69, 7, 9), False),
    "blackstone": ((42, 36, 40), False),
    "polished_blackstone": ((52, 47, 53), False),
    "polished_blackstone_bricks": ((48, 43, 49), False),
    "gilded_blackstone": ((60, 45, 40), False),
    "basalt": ((69, 68, 72), False),
    "smooth_basalt": ((79, 79, 82), False),
    "end_stone": ((219, 219, 165), False),
    "end_stone_bricks": ((223, 223, 172), False),
    "terracotta": ((152, 94, 68), False),
    "white_terracotta": ((209, 178, 161), False),
    "orange_terracotta": ((161, 83, 37), False),
    "light_gray_terracotta": ((135, 107, 98), False),
    "gray_terracotta": ((57, 42, 35), False),
    "brown_terracotta": ((77, 51, 36), False),
    "black_terracotta": ((37, 22, 16), False),
    # --- Wood: planks ---
    "oak_planks": ((162, 130, 78), False),
    "spruce_planks": ((114, 84, 48), False),
    "birch_planks": ((192, 175, 121), False),
    "jungle_planks": ((160, 115, 80), False),
    "acacia_planks": ((168, 90, 50), False),
    "dark_oak_planks": ((67, 43, 21), False),
    "mangrove_planks": ((117, 54, 48), False),
    "cherry_planks": ((227, 180, 165), False),
    "crimson_planks": ((101, 48, 68), False),
    "warped_planks": ((43, 104, 99), False),
    # --- Wood: logs ---
    "oak_log": ((108, 89, 55), False),
    "spruce_log": ((65, 47, 28), False),
    "birch_log": ((216, 210, 203), False),
    "jungle_log": ((85, 68, 39), False),
    "acacia_log": ((103, 79, 56), False),
    "dark_oak_log": ((60, 47, 29), False),
    "mangrove_log": ((89, 61, 61), False),
    "cherry_log": ((54, 32, 33), False),
    "crimson_stem": ((110, 46, 82), False),
    "warped_stem": ((52, 104, 101), False),
    "stripped_oak_log": ((169, 135, 82), False),
    "stripped_dark_oak_log": ((89, 65, 42), False),
    # --- Glass ---
    "glass": ((220, 237, 237), True),
    "white_stained_glass": ((224, 224, 224), True),
    "orange_stained_glass": ((216, 127, 51), True),
    "light_blue_stained_glass": ((102, 153, 216), True),
    "blue_stained_glass": ((51, 76, 178), True),
    "green_stained_glass": ((94, 124, 22), True),
    "black_stained_glass": ((25, 25, 25), True),
    "glass_pane": ((220, 237, 237), True),
    # --- Wool / concrete (representative colors) ---
    "white_wool": ((233, 236, 236), False),
    "light_gray_wool": ((142, 142, 134), False),
    "gray_wool": ((62, 68, 71), False),
    "black_wool": ((20, 21, 25), False),
    "red_wool": ((161, 39, 34), False),
    "orange_wool": ((240, 118, 19), False),
    "yellow_wool": ((248, 197, 39), False),
    "lime_wool": ((112, 185, 25), False),
    "green_wool": ((84, 109, 27), False),
    "cyan_wool": ((21, 137, 145), False),
    "light_blue_wool": ((58, 175, 217), False),
    "blue_wool": ((53, 57, 157), False),
    "purple_wool": ((121, 42, 172), False),
    "magenta_wool": ((189, 68, 179), False),
    "pink_wool": ((238, 141, 172), False),
    "brown_wool": ((114, 71, 40), False),
    "white_concrete": ((207, 213, 214), False),
    "light_gray_concrete": ((125, 125, 115), False),
    "gray_concrete": ((54, 57, 61), False),
    "black_concrete": ((8, 10, 15), False),
    "red_concrete": ((142, 32, 32), False),
    "orange_concrete": ((224, 97, 1), False),
    "yellow_concrete": ((241, 175, 21), False),
    "lime_concrete": ((94, 168, 24), False),
    "green_concrete": ((73, 91, 36), False),
    "cyan_concrete": ((21, 119, 136), False),
    "light_blue_concrete": ((36, 137, 199), False),
    "blue_concrete": ((44, 46, 143), False),
    "purple_concrete": ((100, 32, 156), False),
    "brown_concrete": ((96, 60, 32), False),
    # --- Misc / functional ---
    "dirt": ((134, 96, 67), False),
    "coarse_dirt": ((121, 90, 64), False),
    "podzol": ((105, 74, 38), False),
    "grass_block": ((127, 178, 56), False),
    "mycelium": ((111, 98, 97), False),
    "clay": ((159, 164, 177), False),
    "packed_mud": ((152, 118, 84), False),
    "snow_block": ((249, 254, 254), False),
    "ice": ((140, 179, 237), True),
    "packed_ice": ((141, 180, 238), False),
    "iron_block": ((220, 220, 220), False),
    "chain": ((66, 66, 66), False),
    "gold_block": ((247, 223, 82), False),
    "diamond_block": ((98, 237, 220), False),
    "emerald_block": ((60, 178, 90), False),
    "netherite_block": ((67, 61, 63), False),
    "copper_block": ((191, 111, 80), False),
    "oxidized_copper": ((82, 162, 132), False),
    "glowstone": ((248, 202, 91), False),
    "sea_lantern": ((197, 219, 209), False),
    "shroomlight": ((245, 151, 68), False),
    "water": ((63, 118, 228), True),
    "lava": ((207, 92, 20), False),
    "hay_block": ((168, 143, 22), False),
    "bookshelf": ((109, 88, 54), False),
    "oak_leaves": ((60, 92, 30), True),
    "spruce_leaves": ((56, 79, 55), True),
    "birch_leaves": ((72, 100, 45), True),
    "jungle_leaves": ((43, 113, 21), True),
    "dark_oak_leaves": ((56, 82, 30), True),
    "azalea_leaves": ((100, 118, 54), True),
}


def _canonical_base_id(name: str) -> str:
    """Normalize a registry/input block name to a canonical `namespace:path` ID."""
    name = name.strip()
    if not name:
        raise ValueError("Block name must not be empty.")
    if ":" not in name:
        return f"minecraft:{name}"
    namespace, path = name.split(":", 1)
    namespace = namespace.strip()
    path = path.strip()
    if not namespace or not path:
        raise ValueError(f"Invalid namespaced block ID: {name!r}")
    return f"{namespace}:{path}"


def _display_base_id(base_id: str) -> str:
    """Keep vanilla names terse while preserving namespaces for modded blocks."""
    return base_id.removeprefix("minecraft:")


@lru_cache(maxsize=1)
def _load_registry_ids() -> tuple[str, ...]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    ids: list[str] = []
    seen: set[str] = set()
    for entry in raw:
        base_id = _canonical_base_id(str(entry))
        namespace, path = base_id.split(":", 1)
        if namespace == "minecraft" and path in _EXCLUDED_NAMES:
            continue
        if base_id not in seen:
            ids.append(base_id)
            seen.add(base_id)
    return tuple(ids)


@cache
def _texture_derived_color(name: str) -> tuple[tuple[int, int, int], bool] | None:
    from mcbuild.render import textures  # local import: avoids a palette<->render import cycle

    tex = textures.get_face_texture(name, "side") or textures.get_face_texture(name, "top")
    if tex is None:
        return None
    pixels = list(tex.convert("RGBA").tobytes())
    pixels = list(zip(pixels[0::4], pixels[1::4], pixels[2::4], pixels[3::4], strict=True))
    opaque = [p for p in pixels if p[3] > 10]
    if not opaque:
        return None
    n = len(opaque)
    rgb = (
        sum(p[0] for p in opaque) // n,
        sum(p[1] for p in opaque) // n,
        sum(p[2] for p in opaque) // n,
    )
    transparent = any(p[3] < 250 for p in pixels)
    return rgb, transparent


def _resolve(base_id: str) -> tuple[tuple[int, int, int], bool] | None:
    """Resolve (rgb, transparent) from bundled vanilla or imported mod resources."""
    namespace, name = base_id.split(":", 1)
    if namespace == "minecraft":
        curated = _CURATED.get(name)
        if curated is not None:
            return curated

    direct = _texture_derived_color(base_id)
    if direct is not None:
        return direct

    from mcbuild.render import blockmodel  # local import: avoids an import cycle

    representative = blockmodel.representative_texture(base_id)
    if representative is not None and representative != base_id:
        return _texture_derived_color(representative)
    return None


_DEFAULT_IDS = _load_registry_ids()
_IDS = _DEFAULT_IDS
_ID_TO_INDEX: dict[str, int] = {base_id: i for i, base_id in enumerate(_IDS)}
_N_BASE = len(_IDS)
_ACTIVE_PROFILE: ServerProfile | None = None
_STATE_PROPERTIES: dict[str, dict[str, frozenset[str]]] = {}
_VALID_STATE_PAIRS: dict[str, tuple[frozenset[tuple[str, str]], ...]] = {}

# Stateful blocks ("oak_stairs[facing=north,...]") get indices allocated above the base
# registry range, on first use.
_dynamic_index: dict[str, int] = {}
_index_block: dict[int, Block] = {}


def _parse_name(name: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Split a block string into canonical base ID + sorted state properties."""
    if name.endswith("]") and "[" in name:
        base, rest = name.split("[", 1)
        pairs = []
        for part in rest[:-1].split(","):
            part = part.strip()
            if not part:
                continue
            k, _, v = part.partition("=")
            pairs.append((k.strip(), v.strip()))
        return _canonical_base_id(base), tuple(sorted(pairs))
    return _canonical_base_id(name), ()


def _mc_id(base_id: str, state: tuple[tuple[str, str], ...]) -> str:
    if not state:
        return base_id
    props = ",".join(f"{k}={v}" for k, v in state)
    return f"{base_id}[{props}]"


def _build_block(index: int, base_id: str, state: tuple[tuple[str, str], ...]) -> Block:
    namespace, name = base_id.split(":", 1)
    resolved = _resolve(base_id)
    if resolved is None:
        return Block(
            index=index,
            namespace=namespace,
            name=name,
            mc_id=_mc_id(base_id, state),
            rgb=(0, 0, 0),
            renderable=False,
            state=state,
        )
    rgb, transparent = resolved
    return Block(
        index=index,
        namespace=namespace,
        name=name,
        mc_id=_mc_id(base_id, state),
        rgb=rgb,
        transparent=transparent,
        state=state,
    )


@cache
def _base_block(index: int) -> Block:
    return _build_block(index, _IDS[index], ())


def configure_server_profile(profile: ServerProfile | None) -> None:
    """Switch palette validation to an exported live-server registry profile."""
    global _ACTIVE_PROFILE, _IDS, _ID_TO_INDEX, _N_BASE, _STATE_PROPERTIES, _VALID_STATE_PAIRS

    if profile is None:
        ids = _DEFAULT_IDS
        properties: dict[str, dict[str, frozenset[str]]] = {}
        valid_states: dict[str, tuple[frozenset[tuple[str, str]], ...]] = {}
    else:
        ids_list: list[str] = []
        properties = {}
        valid_states = {}
        for base_id, entry in profile.blocks.items():
            namespace, path = base_id.split(":", 1)
            if namespace == "minecraft" and path in _EXCLUDED_NAMES:
                continue

            ids_list.append(base_id)
            properties[base_id] = {
                key: frozenset(str(value) for value in values) for key, values in entry["properties"].items()
            }
            valid_states[base_id] = tuple(frozenset(_parse_name(state_name)[1]) for state_name in entry["states"])
        ids = tuple(ids_list)

    _ACTIVE_PROFILE = profile
    _IDS = ids
    _ID_TO_INDEX = {base_id: i for i, base_id in enumerate(_IDS)}
    _N_BASE = len(_IDS)
    _STATE_PROPERTIES = properties
    _VALID_STATE_PAIRS = valid_states
    _dynamic_index.clear()
    _index_block.clear()
    _base_block.cache_clear()


def configure_server_registry(path: str | Path) -> ServerProfile:
    """Load an exported registry JSON and make it the active palette source."""
    profile = ServerProfile.load(path)
    configure_server_profile(profile)
    return profile


def registry_metadata() -> dict:
    """Describe the active palette source without exposing local filesystem paths."""
    if _ACTIVE_PROFILE is None:
        return {
            "source": "bundled",
            "block_count": len(_IDS),
            "minecraft_version": None,
            "data_version": None,
            "namespaces": {"minecraft": len(_IDS)},
        }
    metadata = _ACTIVE_PROFILE.metadata()
    metadata.pop("source", None)
    metadata["source"] = "server-export"
    return metadata


def _validate_state(base_id: str, state: tuple[tuple[str, str], ...]) -> None:
    if _ACTIVE_PROFILE is None or not state:
        return

    properties = _STATE_PROPERTIES.get(base_id, {})
    seen: set[str] = set()
    for key, value in state:
        if key in seen:
            raise PaletteError(f"Duplicate block-state property '{key}' for '{base_id}'.")
        seen.add(key)

        allowed = properties.get(key)
        if allowed is None:
            known = ", ".join(sorted(properties)) or "(none)"
            raise PaletteError(f"Invalid state property '{key}' for '{base_id}'. Valid properties: {known}.")
        if value not in allowed:
            choices = ", ".join(sorted(allowed))
            raise PaletteError(f"Invalid value '{value}' for '{base_id}[{key}=...]'. Valid values: {choices}.")

    requested = frozenset(state)
    valid_states = _VALID_STATE_PAIRS.get(base_id, ())
    if valid_states and not any(requested.issubset(candidate) for candidate in valid_states):
        raise PaletteError(f"Invalid block-state combination for '{_mc_id(base_id, state)}'.")


def get_block(name: str) -> Block:
    """Look up a block by name with optional state.

    Unqualified names remain backward-compatible aliases for the `minecraft`
    namespace. Fully-qualified IDs such as `create:andesite_casing` are preserved
    verbatim and validated against the configured registry.
    """
    base_id, state = _parse_name(name)
    namespace, path = base_id.split(":", 1)

    if namespace == "minecraft":
        aliased = ALIAS.get(path)
        if aliased is not None:
            _warnings.append(f"'{path}' is not a valid block name; substituted alias '{aliased}'.")
            base_id = f"minecraft:{aliased}"

    index = _ID_TO_INDEX.get(base_id)
    if index is None:
        match = _confident_match(base_id)
        if match is not None:
            _warnings.append(
                f"Unknown block '{_display_base_id(base_id)}'; "
                f"auto-corrected to close match '{_display_base_id(match)}'."
            )
            base_id = match
            index = _ID_TO_INDEX[base_id]
        else:
            suggestions = suggest(base_id)
            hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            raise PaletteError(f"Unknown block '{_display_base_id(base_id)}'.{hint}")

    _validate_state(base_id, state)

    if not state:
        return _base_block(index)

    key = _mc_id(base_id, state)
    dyn = _dynamic_index.get(key)
    if dyn is None:
        dyn = _N_BASE + len(_dynamic_index)
        _dynamic_index[key] = dyn
        _index_block[dyn] = _build_block(dyn, base_id, state)
    return _index_block[dyn]


def get_block_by_index(index: int) -> Block:
    if index < _N_BASE:
        return _base_block(index)
    return _index_block[index]


def _same_namespace_ids(base_id: str) -> list[str]:
    namespace = base_id.split(":", 1)[0]
    prefix = f"{namespace}:"
    return [candidate for candidate in _IDS if candidate.startswith(prefix)]


def _namespace_matches(base_id: str, n: int, cutoff: float) -> list[str]:
    """Fuzzy-match only the namespace-local path.

    Comparing full IDs artificially inflates similarity because every candidate
    shares the namespace prefix, which can turn excluded/unknown blocks into
    unsafe auto-corrections.
    """
    _, path = base_id.split(":", 1)
    candidates = _same_namespace_ids(base_id)
    by_path = {candidate.split(":", 1)[1]: candidate for candidate in candidates}
    path_hits = difflib.get_close_matches(path, list(by_path), n=n, cutoff=cutoff)
    return [by_path[path_hit] for path_hit in path_hits]


def suggest(name: str, n: int = 3) -> list[str]:
    base_id, _ = _parse_name(name)
    hits = _namespace_matches(base_id, n=n, cutoff=0.4)
    return [_display_base_id(hit) for hit in hits]


def _confident_match(base_id: str) -> str | None:
    """A single close path match in the same namespace at a strict cutoff."""
    hits = _namespace_matches(base_id, n=1, cutoff=0.82)
    return hits[0] if hits else None


def all_block_ids() -> list[str]:
    """Return canonical namespaced IDs from the configured registry."""
    return list(_IDS)


def all_block_names() -> list[str]:
    """Backward-compatible display names: bare vanilla paths, namespaced modded IDs."""
    return [_display_base_id(base_id) for base_id in _IDS]
