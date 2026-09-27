"""Real Minecraft block texture lookup + biome-tint approximation.

Textures ship at src/mcbuild/assets/textures/block/. Blocks without a matching
texture fall back to the flat palette color (handled by the sprite builder in
iso.py), so this module is purely additive.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import cast

from PIL import Image

from mcbuild.render import resources

TEXTURE_DIR = Path(__file__).resolve().parent.parent / "assets" / "textures" / "block"
TEXTURE_SIZE = 16

# Vanilla resource-pack textures for these blocks are grayscale tint masks,
# colorized per-biome at render time. We approximate the tint with this
# project's own curated palette RGB (palette.py) instead of a biome lookup.
TINTED_TOP_ONLY = {"grass_block"}
TINTED_ALL_FACES = {
    "oak_leaves",
    "spruce_leaves",
    "birch_leaves",
    "jungle_leaves",
    "acacia_leaves",
    "dark_oak_leaves",
    "mangrove_leaves",
    "azalea_leaves",
}


@cache
def _load(path: Path) -> Image.Image | None:
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        return None
    if img.size != (TEXTURE_SIZE, TEXTURE_SIZE):
        img = img.resize((TEXTURE_SIZE, TEXTURE_SIZE), Image.Resampling.NEAREST)
    return img


def _candidates(name: str, face: str) -> list[str]:
    namespace, path = resources.split_resource_location(name)
    if path.startswith("block/") or path.startswith("textures/"):
        return [f"{namespace}:{path}"]
    if face == "top":
        paths = [f"{path}_top", path]
    elif face == "bottom":
        paths = [f"{path}_bottom", f"{path}_top", path]
    else:
        paths = [f"{path}_side", path]
    return [f"{namespace}:{candidate}" for candidate in paths]


@cache
def get_face_texture(name: str, face: str) -> Image.Image | None:
    """Return a 16x16 RGBA texture for a vanilla or namespaced mod resource."""
    for candidate in _candidates(name, face):
        path = resources.texture_path(candidate)
        if path is None:
            continue
        img = _load(path)
        if img is not None:
            return img
    return None


def configure_mod_asset_cache(path: str | Path | None) -> None:
    """Point texture lookup at another imported mod resource-pack cache."""
    resources.configure_cache_root(path)
    _load.cache_clear()
    get_face_texture.cache_clear()


def needs_tint(name: str, face: str) -> bool:
    namespace, path = resources.split_resource_location(name)
    if namespace != "minecraft":
        return False
    if path in TINTED_ALL_FACES:
        return True
    return face == "top" and path in TINTED_TOP_ONLY


def apply_tint(img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    r, g, b = rgb
    tinted = Image.new("RGBA", img.size)
    src = img.load()
    dst = tinted.load()
    assert src is not None and dst is not None
    for y in range(img.height):
        for x in range(img.width):
            # `img` is RGBA mode, so indexing always yields a 4-tuple.
            pr, pg, pb, pa = cast(tuple[int, int, int, int], src[x, y])
            dst[x, y] = (pr * r // 255, pg * g // 255, pb * b // 255, pa)
    return tinted
