"""Parse bundled vanilla blockstate JSON into (model, rotation) parts for a given state.

Handles both `variants` (stairs/slabs/doors/...) and `multipart` (walls/fences/panes).
We only need each matched part's model name (its suffix identifies the geometry template)
and its x/y rotation in degrees; textures come from our own texture heuristic, not the
referenced model file (which we don't ship).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from mcbuild.render import resources

BLOCKSTATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "blockstates"


@dataclass(frozen=True)
class ModelPart:
    model: str  # bare model name, e.g. "oak_stairs_inner"
    x: int = 0  # rotation about the X axis, degrees (0/90/180/270)
    y: int = 0  # rotation about the Y axis, degrees


@cache
def _load_blockstate(name: str) -> dict | None:
    path = resources.blockstate_path(name)
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def configure_mod_asset_cache(path: str | Path | None) -> None:
    resources.configure_cache_root(path)
    _load_blockstate.cache_clear()


def _model_ref(ref, default_namespace: str) -> str:
    if isinstance(ref, list):
        ref = ref[0]  # a weighted variant list; take the first
    model = ref.get("model", "") if isinstance(ref, dict) else str(ref)
    return resources.canonical_resource_location(model, default_namespace)


def _variant_to_part(entry: dict, default_namespace: str) -> ModelPart:
    if isinstance(entry, list):
        entry = entry[0]
    return ModelPart(
        model=_model_ref(entry, default_namespace),
        x=int(entry.get("x", 0)) % 360,
        y=int(entry.get("y", 0)) % 360,
    )


def _variant_key_matches(key: str, state: dict[str, str]) -> bool:
    """A variant key "a=1,b=2" matches iff every listed prop equals the state's value."""
    if key == "":
        return True
    for cond in key.split(","):
        prop, _, val = cond.partition("=")
        if str(state.get(prop, "")) != val:
            return False
    return True


def _when_matches(when: dict, state: dict[str, str]) -> bool:
    if not when:
        return True
    if "OR" in when:
        return any(_when_matches(sub, state) for sub in when["OR"])
    if "AND" in when:
        return all(_when_matches(sub, state) for sub in when["AND"])
    for prop, expected in when.items():
        actual = str(state.get(prop, ""))
        # values may be pipe-separated alternatives: "low|tall"
        if actual not in str(expected).split("|"):
            return False
    return True


def resolve_parts(name: str, state: dict[str, str]) -> list[ModelPart] | None:
    """Return the model parts for `name` in the given state, or None if not modelled here.

    None means "no blockstate JSON for this block" — caller should use a full-cube fallback.
    An empty list means the state matched nothing (also treat as full-cube fallback).
    """
    data = _load_blockstate(name)
    if data is None:
        return None

    default_namespace, _ = resources.split_resource_location(name)

    if "variants" in data:
        variants = data["variants"]
        # exact match first, then any key whose listed props all match
        for key, entry in variants.items():
            if _variant_key_matches(key, state):
                return [_variant_to_part(entry, default_namespace)]
        return []

    if "multipart" in data:
        parts: list[ModelPart] = []
        for rule in data["multipart"]:
            if _when_matches(rule.get("when", {}), state):
                parts.append(_variant_to_part(rule["apply"], default_namespace))
        return parts

    return None


def first_model(name: str) -> str | None:
    """Return the first model reference from a blockstate, ignoring state conditions."""
    data = _load_blockstate(name)
    if data is None:
        return None
    default_namespace, _ = resources.split_resource_location(name)
    variants = data.get("variants")
    if isinstance(variants, dict) and variants:
        return _model_ref(next(iter(variants.values())), default_namespace)
    multipart = data.get("multipart")
    if isinstance(multipart, list) and multipart:
        first = multipart[0]
        if isinstance(first, dict) and "apply" in first:
            return _model_ref(first["apply"], default_namespace)
    return None
