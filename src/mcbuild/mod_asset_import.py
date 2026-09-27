"""Import scanned mod resources into a local resource-pack cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from dotenv import load_dotenv

INDEX_ENV = "MCBUILD_MOD_ASSET_INDEX"
CACHE_ENV = "MCBUILD_MOD_ASSET_CACHE"
DEFAULT_INDEX = Path(".mcbuild") / "mod-assets-index.json"
DEFAULT_CACHE = Path(".mcbuild") / "resourcepack"
CACHE_MANIFEST = "mod-assets-cache.json"
CACHE_FORMAT_VERSION = 1

_RESOURCE_KEYS = ("blockstates", "block_models", "block_textures", "block_texture_meta")


class ModAssetImportError(ValueError):
    """Raised when a scanned mod manifest cannot be imported safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_index_path(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    value = os.getenv(INDEX_ENV)
    return Path(value).expanduser() if value else DEFAULT_INDEX


def resolve_cache_dir(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    value = os.getenv(CACHE_ENV)
    return Path(value).expanduser() if value else DEFAULT_CACHE


def _load_index(path: Path) -> dict[str, Any]:
    source = path.expanduser().resolve()
    if not source.is_file():
        raise ModAssetImportError(f"Mod asset index not found: {source}")

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModAssetImportError(f"Could not read mod asset index {source}: {exc}") from exc

    if data.get("format_version") != 1:
        raise ModAssetImportError(
            f"Unsupported mod asset index format_version={data.get('format_version')!r}; expected 1."
        )
    if not isinstance(data.get("mods_dir"), str):
        raise ModAssetImportError("Mod asset index is missing mods_dir.")
    if not isinstance(data.get("jars"), list):
        raise ModAssetImportError("Mod asset index is missing jars.")
    return data


def _safe_resource_path(resource: str) -> PurePosixPath:
    path = PurePosixPath(resource)
    if not resource or path.is_absolute() or ".." in path.parts:
        raise ModAssetImportError(f"Unsafe resource path in mod asset index: {resource!r}")
    if len(path.parts) < 4 or path.parts[0] != "assets":
        raise ModAssetImportError(f"Unexpected resource path in mod asset index: {resource!r}")
    return path


def _resource_paths(jar_record: dict[str, Any]) -> list[str]:
    result: set[str] = set()
    namespaces = jar_record.get("namespaces")
    if not isinstance(namespaces, dict):
        return []

    for namespace_data in namespaces.values():
        if not isinstance(namespace_data, dict):
            continue
        for key in _RESOURCE_KEYS:
            values = namespace_data.get(key, [])
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, str):
                    result.add(value)
    return sorted(result)


def import_mod_assets(
    index_path: str | Path = DEFAULT_INDEX,
    cache_dir: str | Path = DEFAULT_CACHE,
) -> dict[str, Any]:
    """Extract only indexed render assets from mod JARs into a deterministic cache."""
    index = _load_index(Path(index_path))
    mods_dir = Path(index["mods_dir"]).expanduser().resolve()
    if not mods_dir.is_dir():
        raise ModAssetImportError(f"Mods directory from index no longer exists: {mods_dir}")

    destination = Path(cache_dir).expanduser().resolve()
    staging = destination.with_name(destination.name + ".tmp")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    providers: dict[str, list[str]] = {}
    conflicts: list[dict[str, Any]] = []
    imported_files: set[str] = set()
    jar_summaries: list[dict[str, Any]] = []

    try:
        for jar_record in index["jars"]:
            if not isinstance(jar_record, dict):
                continue
            resources = _resource_paths(jar_record)
            if not resources:
                continue

            filename = jar_record.get("file")
            expected_hash = jar_record.get("sha256")
            if not isinstance(filename, str) or not filename:
                raise ModAssetImportError("A JAR record with assets is missing its filename.")
            if not isinstance(expected_hash, str) or not expected_hash:
                raise ModAssetImportError(f"JAR record {filename} is missing sha256.")

            jar_path = mods_dir / filename
            if not jar_path.is_file():
                raise ModAssetImportError(
                    f"Indexed mod JAR is missing: {jar_path}. Re-run mcbuild-scan-mods."
                )

            actual_hash = _sha256(jar_path)
            if actual_hash != expected_hash:
                raise ModAssetImportError(
                    f"JAR changed since the scan: {filename}. Re-run mcbuild-scan-mods before importing."
                )

            imported_from_jar = 0
            try:
                with zipfile.ZipFile(jar_path) as archive:
                    names = set(archive.namelist())
                    for resource in resources:
                        safe = _safe_resource_path(resource)
                        if resource not in names:
                            raise ModAssetImportError(
                                f"Indexed resource {resource!r} is missing from {filename}. "
                                "Re-run mcbuild-scan-mods."
                            )

                        payload = archive.read(resource)
                        target = staging.joinpath(*safe.parts)
                        key = safe.as_posix()
                        previous_providers = providers.setdefault(key, [])

                        if target.exists():
                            previous = target.read_bytes()
                            if previous != payload:
                                conflicts.append(
                                    {
                                        "resource": key,
                                        "previous_providers": list(previous_providers),
                                        "winner": filename,
                                    }
                                )

                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(payload)
                        previous_providers.append(filename)
                        imported_files.add(key)
                        imported_from_jar += 1
            except zipfile.BadZipFile as exc:
                raise ModAssetImportError(f"Could not open indexed JAR {jar_path}: {exc}") from exc

            jar_summaries.append(
                {
                    "file": filename,
                    "sha256": actual_hash,
                    "imported_resource_count": imported_from_jar,
                }
            )

        if destination.exists():
            shutil.rmtree(destination)
        os.replace(staging, destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    namespaces = sorted(
        {
            PurePosixPath(resource).parts[1]
            for resource in imported_files
            if len(PurePosixPath(resource).parts) >= 2
        }
    )
    manifest = {
        "format_version": CACHE_FORMAT_VERSION,
        "source_index": str(Path(index_path).expanduser().resolve()),
        "mods_dir": str(mods_dir),
        "cache_dir": str(destination),
        "imported_resource_count": len(imported_files),
        "namespace_count": len(namespaces),
        "namespaces": namespaces,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "jars": jar_summaries,
    }
    cache_manifest_path = destination.parent / CACHE_MANIFEST
    cache_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Import scanned Minecraft mod resources into the local BuildAI render cache."
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=None,
        help=f"Scanner manifest. Defaults to {INDEX_ENV} or {DEFAULT_INDEX}.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=f"Resource-pack cache directory. Defaults to {CACHE_ENV} or {DEFAULT_CACHE}.",
    )
    args = parser.parse_args()

    try:
        manifest = import_mod_assets(
            resolve_index_path(args.index),
            resolve_cache_dir(args.cache_dir),
        )
    except ModAssetImportError as exc:
        parser.error(str(exc))

    print(f"Imported resources: {manifest['imported_resource_count']:,}")
    print(f"Namespaces: {manifest['namespace_count']}")
    print(f"Conflicts: {manifest['conflict_count']}")
    print(f"Cache: {manifest['cache_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
