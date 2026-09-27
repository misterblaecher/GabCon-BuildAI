"""Scan Minecraft mod JARs and inventory render-relevant resource-pack assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tomllib
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

DEFAULT_MODS_DIR = Path(r"A:\MinecraftServer\mods")
MODS_DIR_ENV = "MCBUILD_MODS_DIR"
MANIFEST_VERSION = 1

_ASSET_KINDS = {
    "blockstates": ("blockstates", ".json"),
    "block_models": ("models/block", ".json"),
    "block_textures": ("textures/block", ".png"),
    "block_texture_meta": ("textures/block", ".png.mcmeta"),
}


class ModScanError(ValueError):
    """Raised when the mods directory cannot be scanned."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _toml_mods(archive: zipfile.ZipFile) -> list[dict[str, str]]:
    descriptor = None
    for candidate in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        try:
            descriptor = archive.read(candidate)
            break
        except KeyError:
            continue

    if descriptor is None:
        return []

    try:
        data = tomllib.loads(descriptor.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return []

    mods = data.get("mods")
    if not isinstance(mods, list):
        return []

    result: list[dict[str, str]] = []
    for entry in mods:
        if not isinstance(entry, dict):
            continue
        mod_id = entry.get("modId")
        if not isinstance(mod_id, str) or not mod_id:
            continue
        record = {"id": mod_id}
        version = entry.get("version")
        display_name = entry.get("displayName")
        if isinstance(version, str) and version:
            record["version"] = version
        if isinstance(display_name, str) and display_name:
            record["display_name"] = display_name
        result.append(record)
    return result


def _fabric_mod(archive: zipfile.ZipFile) -> list[dict[str, str]]:
    try:
        raw = archive.read("fabric.mod.json")
    except KeyError:
        return []

    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []

    mod_id = data.get("id")
    if not isinstance(mod_id, str) or not mod_id:
        return []

    record = {"id": mod_id}
    version = data.get("version")
    name = data.get("name")
    if isinstance(version, str) and version:
        record["version"] = version
    if isinstance(name, str) and name:
        record["display_name"] = name
    return [record]


def _resource_info(name: str) -> tuple[str, str] | None:
    """Return (namespace, asset_kind) for a render-relevant resource path."""
    path = PurePosixPath(name)
    parts = path.parts
    if len(parts) < 4 or parts[0] != "assets":
        return None

    namespace = parts[1]
    relative = "/".join(parts[2:])
    if not namespace or not relative:
        return None

    for kind, (prefix, suffix) in _ASSET_KINDS.items():
        if relative.startswith(prefix + "/") and relative.endswith(suffix):
            return namespace, kind
    return None


def _scan_jar(path: Path) -> dict[str, Any]:
    assets: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    total_asset_files = 0

    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.startswith("assets/"):
                total_asset_files += 1
            match = _resource_info(name)
            if match is None:
                continue
            namespace, kind = match
            assets[namespace][kind].append(name)

        mods = _toml_mods(archive)
        if not mods:
            mods = _fabric_mod(archive)

    namespaces: dict[str, Any] = {}
    for namespace in sorted(assets):
        kinds = assets[namespace]
        namespace_record: dict[str, Any] = {}
        for kind in _ASSET_KINDS:
            paths = sorted(kinds.get(kind, []))
            namespace_record[kind] = paths
            namespace_record[f"{kind}_count"] = len(paths)
        namespace_record["render_asset_count"] = sum(
            int(namespace_record[f"{kind}_count"]) for kind in _ASSET_KINDS
        )
        namespaces[namespace] = namespace_record

    return {
        "file": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "mods": mods,
        "total_asset_files": total_asset_files,
        "namespaces": namespaces,
    }


def resolve_mods_dir(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    env_value = os.getenv(MODS_DIR_ENV)
    return Path(env_value).expanduser() if env_value else DEFAULT_MODS_DIR


def scan_mod_directory(mods_dir: str | Path) -> dict[str, Any]:
    root = Path(mods_dir).expanduser().resolve()
    if not root.is_dir():
        raise ModScanError(f"Mods directory not found: {root}")

    jars = sorted(
        (path for path in root.iterdir() if path.is_file() and path.suffix.lower() == ".jar"),
        key=lambda path: path.name.lower(),
    )

    jar_records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    providers: dict[str, list[str]] = defaultdict(list)
    totals = {kind: 0 for kind in _ASSET_KINDS}

    for jar in jars:
        try:
            record = _scan_jar(jar)
        except (OSError, zipfile.BadZipFile) as exc:
            errors.append({"file": jar.name, "error": str(exc)})
            continue

        jar_records.append(record)
        for namespace, namespace_data in record["namespaces"].items():
            providers[namespace].append(jar.name)
            for kind in _ASSET_KINDS:
                totals[kind] += int(namespace_data[f"{kind}_count"])

    namespace_providers = {
        namespace: sorted(files, key=str.lower) for namespace, files in sorted(providers.items())
    }

    return {
        "format_version": MANIFEST_VERSION,
        "mods_dir": str(root),
        "jar_count": len(jars),
        "scanned_jar_count": len(jar_records),
        "error_count": len(errors),
        "namespace_count": len(namespace_providers),
        "namespace_providers": namespace_providers,
        "totals": {
            **totals,
            "render_assets": sum(totals.values()),
        },
        "jars": jar_records,
        "errors": errors,
    }


def write_manifest(manifest: dict[str, Any], output: str | Path) -> Path:
    destination = Path(output).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Minecraft mod JARs for blockstates, block models and block textures."
    )
    parser.add_argument(
        "--mods-dir",
        type=Path,
        default=None,
        help=f"Mods directory. Defaults to {MODS_DIR_ENV} or {DEFAULT_MODS_DIR}.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(".mcbuild") / "mod-assets-index.json",
        help="JSON manifest destination.",
    )
    args = parser.parse_args()

    try:
        mods_dir = resolve_mods_dir(args.mods_dir)
        manifest = scan_mod_directory(mods_dir)
        output = write_manifest(manifest, args.out)
    except ModScanError as exc:
        parser.error(str(exc))

    print(f"Mods directory: {manifest['mods_dir']}")
    print(
        f"JARs: {manifest['scanned_jar_count']}/{manifest['jar_count']} scanned"
        f" ({manifest['error_count']} error(s))"
    )
    print(f"Namespaces with render assets: {manifest['namespace_count']}")
    print(f"Render assets indexed: {manifest['totals']['render_assets']:,}")
    print(f"Manifest: {output}")

    for namespace, files in manifest["namespace_providers"].items():
        print(f"  {namespace}: {', '.join(files)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
