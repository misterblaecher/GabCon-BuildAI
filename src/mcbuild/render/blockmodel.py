"""Block geometry: (name, state) -> list of textured cuboid faces in a 0..1 unit cell.

Full-cube blocks are a single box. Stateful architectural blocks (stairs, slabs, walls,
fences, fence gates, trapdoors, doors, panes) use hardcoded geometry templates keyed by the
model name from the bundled vanilla blockstate JSON (see blockstate.py), rotated by the
rotation that blockstate specifies. Textures are resolved from the block's base material via
the existing texture set (we don't ship the vanilla model JSONs).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import cache, lru_cache

from mcbuild.render import blockstate, resources, textures

# A box is (x0, y0, z0, x1, y1, z1) in 0..16 model space.
Box = tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class Face:
    corners: tuple[tuple[float, float, float], ...]  # 4 corners in 0..1 cell space
    normal: tuple[float, float, float]
    uvs: tuple[tuple[float, float], ...]  # per-corner UV in 0..1
    texture: str  # base texture name for textures.get_face_texture
    kind: str  # 'top' | 'bottom' | 'side' (texture + shading class, from final normal)
    tint: bool


# --- box -> faces (before rotation), in 0..16 space ---

_Corner = tuple[float, float, float]
_Normal = tuple[int, int, int]
_Uv = tuple[float, float]


# each face: (normal, 4 corners as (x,y,z), 4 uvs) using box min/max
def _box_faces(box: Box) -> list[tuple[_Normal, list[_Corner], list[_Uv]]]:
    x0, y0, z0, x1, y1, z1 = box
    faces: list[tuple[_Normal, list[_Corner]]] = [
        # up (+y)
        ((0, 1, 0), [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)]),
        # down (-y)
        ((0, -1, 0), [(x0, y0, z1), (x0, y0, z0), (x1, y0, z0), (x1, y0, z1)]),
        # north (-z)
        ((0, 0, -1), [(x1, y1, z0), (x1, y0, z0), (x0, y0, z0), (x0, y1, z0)]),
        # south (+z)
        ((0, 0, 1), [(x0, y1, z1), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1)]),
        # west (-x)
        ((-1, 0, 0), [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)]),
        # east (+x)
        ((1, 0, 0), [(x1, y1, z1), (x1, y0, z1), (x1, y0, z0), (x1, y1, z0)]),
    ]
    uvs = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
    return [(n, corners, uvs) for n, corners in faces]


# --- rotation about the cell center (8,8,8), degrees ---


def _rot(px: float, py: float, pz: float, ax: float, ay: float) -> tuple[float, float, float]:
    x, y, z = px - 8.0, py - 8.0, pz - 8.0
    if ax:
        a = math.radians(ax)
        c, s = math.cos(a), math.sin(a)
        y, z = y * c - z * s, y * s + z * c
    if ay:
        a = math.radians(ay)
        c, s = math.cos(a), math.sin(a)
        x, z = x * c + z * s, -x * s + z * c
    return x + 8.0, y + 8.0, z + 8.0


def _classify(normal) -> str:
    nx, ny, nz = normal
    if ny > 0.5:
        return "top"
    if ny < -0.5:
        return "bottom"
    return "side"


# --- shape templates: model-name predicate -> list[Box] (0..16) ---


def _template_boxes(model: str) -> list[Box] | None:
    m = model
    if m.endswith("_stairs_inner"):
        return [(0, 0, 0, 16, 8, 16), (8, 8, 0, 16, 16, 16), (0, 8, 8, 8, 16, 16)]
    if m.endswith("_stairs_outer"):
        return [(0, 0, 0, 16, 8, 16), (8, 8, 8, 16, 16, 16)]
    if m.endswith("_stairs"):
        return [(0, 0, 0, 16, 8, 16), (8, 8, 0, 16, 16, 16)]
    if m.endswith("_slab_top"):
        return [(0, 8, 0, 16, 16, 16)]
    if m.endswith("_slab"):
        return [(0, 0, 0, 16, 8, 16)]
    if m.endswith("_wall_post"):
        return [(4, 0, 4, 12, 16, 12)]
    if m.endswith("_wall_side_tall"):
        return [(5, 0, 0, 11, 16, 8)]
    if m.endswith("_wall_side"):
        return [(5, 0, 0, 11, 14, 8)]
    if m.endswith("_fence_gate"):
        return [(0, 5, 7, 2, 16, 9), (14, 5, 7, 16, 16, 9), (2, 6, 7, 14, 9, 9), (2, 12, 7, 14, 15, 9)]
    if m.endswith("_fence_post"):
        return [(6, 0, 6, 10, 16, 10)]
    if m.endswith("_fence_side"):
        return [(7, 6, 0, 9, 9, 9), (7, 12, 0, 9, 15, 9)]
    if m.endswith("_trapdoor_open"):
        return [(0, 0, 13, 16, 16, 16)]
    if m.endswith("_trapdoor_top"):
        return [(0, 13, 0, 16, 16, 16)]
    if m.endswith("_trapdoor_bottom") or m.endswith("_trapdoor"):
        return [(0, 0, 0, 16, 3, 16)]
    if "_door" in m:
        return [(0, 0, 0, 16, 16, 3)]
    if m.endswith("_bars") or m.endswith("_pane") or "_pane_" in m or "_bars_" in m:
        # thin cross (post + one arm); multipart parts add more arms via rotation
        return [(7, 0, 7, 9, 16, 9)]
    return None


# --- texture/model resolution ---

_SUFFIXES = (
    "_stairs",
    "_slab",
    "_wall",
    "_fence_gate",
    "_fence",
    "_trapdoor",
    "_door",
    "_bars",
    "_pane",
)


@cache
def _base_texture(name: str) -> str | None:
    namespace, path = resources.split_resource_location(name)
    base = path
    for suffix in _SUFFIXES:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    for candidate in (path, base, base + "s", base + "_planks"):
        ref = f"{namespace}:{candidate}"
        if textures.get_face_texture(ref, "side") is not None or textures.get_face_texture(ref, "top") is not None:
            return ref
    return None


@cache
def _load_model(model_ref: str) -> dict | None:
    path = resources.model_path(model_ref)
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@cache
def _model_texture_variables(model_ref: str) -> dict[str, str]:
    data = _load_model(model_ref)
    if data is None:
        return {}

    result: dict[str, str] = {}
    parent = data.get("parent")
    if isinstance(parent, str) and parent:
        parent_ref = resources.canonical_resource_location(parent)
        result.update(_model_texture_variables(parent_ref))

    values = data.get("textures")
    if isinstance(values, dict):
        result.update({str(key): str(value) for key, value in values.items() if isinstance(value, str)})
    return result


def _resolve_texture_variable(value: str, variables: dict[str, str]) -> str | None:
    seen: set[str] = set()
    current = value
    while current.startswith("#"):
        key = current[1:]
        if key in seen:
            return None
        seen.add(key)
        current = variables.get(key, "")
        if not current:
            return None
    return resources.canonical_resource_location(current)


@cache
def _model_face_textures(model_ref: str) -> dict[str, str]:
    variables = _model_texture_variables(model_ref)
    if not variables:
        return {}

    preferred = {
        "top": ("top", "up", "end", "all", "side", "particle"),
        "bottom": ("bottom", "down", "end", "all", "side", "particle"),
        "side": ("side", "north", "front", "all", "particle"),
    }
    result: dict[str, str] = {}
    for kind, keys in preferred.items():
        for key in keys:
            value = variables.get(key)
            if value is None:
                continue
            resolved = _resolve_texture_variable(value, variables)
            if resolved is not None and resources.texture_path(resolved) is not None:
                result[kind] = resolved
                break
    return result


@cache
def representative_texture(name: str) -> str | None:
    """Find one usable texture for palette color derivation and cube fallback."""
    direct = _base_texture(name)
    if direct is not None:
        return direct

    model = blockstate.first_model(name)
    if model is None:
        return None
    face_textures = _model_face_textures(model)
    for kind in ("side", "top", "bottom"):
        if kind in face_textures:
            return face_textures[kind]
    return None


_FULL_CUBE: list[Box] = [(0, 0, 0, 16, 16, 16)]


def _rot_corner(corner: _Corner, ax: float, ay: float) -> _Corner:
    x, y, z = _rot(*corner, ax, ay)
    return x / 16.0, y / 16.0, z / 16.0


def _faces_from_boxes(boxes, ax, ay, tex, tint) -> list[Face]:
    out: list[Face] = []
    for box in boxes:
        for normal, corners, uvs in _box_faces(box):
            rc = tuple(_rot_corner(c, ax, ay) for c in corners)
            rn = _rot(normal[0] + 8, normal[1] + 8, normal[2] + 8, ax, ay)
            rn = (rn[0] - 8.0, rn[1] - 8.0, rn[2] - 8.0)
            kind = _classify(rn)
            texture = tex.get(kind) if isinstance(tex, dict) else tex
            if texture is None and isinstance(tex, dict):
                texture = tex.get("side") or tex.get("top") or tex.get("bottom")
            if texture is None:
                continue
            out.append(
                Face(
                    corners=rc,
                    normal=rn,
                    uvs=tuple(uvs),
                    texture=texture,
                    kind=kind,
                    tint=tint,
                )
            )
    return out


def configure_mod_asset_cache(path) -> None:
    resources.configure_cache_root(path)
    _base_texture.cache_clear()
    _load_model.cache_clear()
    _model_texture_variables.cache_clear()
    _model_face_textures.cache_clear()
    representative_texture.cache_clear()
    get_block_mesh.cache_clear()


@lru_cache(maxsize=4096)
def get_block_mesh(name: str, state_items: tuple = ()) -> list[Face] | None:
    """Return the block's faces in a 0..1 cell, or None if it should not render.

    Mod model JSON is used to choose real namespaced textures. Geometry that does
    not match a supported architectural template intentionally falls back to one
    textured full cube instead of disappearing from the preview.
    """
    state = dict(state_items)
    parts = blockstate.resolve_parts(name, state)
    base_tex = _base_texture(name)
    tint = textures.needs_tint(name, "side") or textures.needs_tint(name, "top")

    if not parts:
        tex = base_tex or representative_texture(name)
        if tex is None:
            return None
        return _faces_from_boxes(_FULL_CUBE, 0, 0, tex, tint)

    faces: list[Face] = []
    matched_template = False
    first_texture = None
    for part in parts:
        model_textures = _model_face_textures(part.model)
        tex = model_textures or base_tex
        if not tex:
            continue
        if first_texture is None:
            first_texture = tex

        boxes = _template_boxes(part.model)
        if boxes is None:
            continue

        matched_template = True
        faces.extend(_faces_from_boxes(boxes, part.x, part.y, tex, tint))

    if matched_template:
        return faces

    tex = first_texture or base_tex or representative_texture(name)
    if tex is None:
        return None
    return _faces_from_boxes(_FULL_CUBE, 0, 0, tex, tint)
