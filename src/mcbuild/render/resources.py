"""Namespaced resource lookup across bundled vanilla assets and imported mod assets."""

from __future__ import annotations

import os
from pathlib import Path

BUNDLED_ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets"
CACHE_ENV = "MCBUILD_MOD_ASSET_CACHE"
DEFAULT_CACHE_ROOT = Path(".mcbuild") / "resourcepack"

_cache_root = Path(os.getenv(CACHE_ENV, DEFAULT_CACHE_ROOT))


def configure_cache_root(path: str | Path | None) -> None:
    global _cache_root
    _cache_root = Path(path).expanduser() if path is not None else Path(os.getenv(CACHE_ENV, DEFAULT_CACHE_ROOT))


def cache_root() -> Path:
    return _cache_root


def split_resource_location(value: str, default_namespace: str = "minecraft") -> tuple[str, str]:
    value = value.strip()
    if ":" in value:
        namespace, path = value.split(":", 1)
    else:
        namespace, path = default_namespace, value
    return namespace, path


def canonical_resource_location(value: str, default_namespace: str = "minecraft") -> str:
    namespace, path = split_resource_location(value, default_namespace)
    return f"{namespace}:{path}"


def blockstate_path(block_id: str) -> Path | None:
    namespace, path = split_resource_location(block_id)
    if namespace == "minecraft":
        candidate = BUNDLED_ASSET_ROOT / "blockstates" / f"{path}.json"
    else:
        candidate = _cache_root / "assets" / namespace / "blockstates" / f"{path}.json"
    return candidate if candidate.is_file() else None


def model_path(model_ref: str, default_namespace: str = "minecraft") -> Path | None:
    namespace, path = split_resource_location(model_ref, default_namespace)
    if path.startswith("models/"):
        relative = f"{path}.json"
    elif path.startswith("block/"):
        relative = f"models/{path}.json"
    else:
        relative = f"models/block/{path}.json"

    if namespace == "minecraft":
        candidate = BUNDLED_ASSET_ROOT / relative
    else:
        candidate = _cache_root / "assets" / namespace / relative
    return candidate if candidate.is_file() else None


def texture_path(texture_ref: str, default_namespace: str = "minecraft") -> Path | None:
    namespace, path = split_resource_location(texture_ref, default_namespace)
    if path.startswith("textures/"):
        relative = f"{path}.png"
    elif path.startswith("block/"):
        relative = f"textures/{path}.png"
    else:
        relative = f"textures/block/{path}.png"

    if namespace == "minecraft":
        candidate = BUNDLED_ASSET_ROOT / relative
    else:
        candidate = _cache_root / "assets" / namespace / relative
    return candidate if candidate.is_file() else None
