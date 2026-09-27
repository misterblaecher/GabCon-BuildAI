"""Build-gallery manifest generation from generated/<build-id>/ artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INDEX_VERSION = 1


def _display_name(build_id: str) -> str:
    return " ".join(part.capitalize() for part in build_id.replace("_", "-").split("-") if part)


def _entry(root: Path, build_dir: Path) -> dict[str, Any] | None:
    stats_path = build_dir / "stats.json"
    render_path = build_dir / "render.png"
    schem_path = build_dir / "final.schem"
    if not (stats_path.is_file() and render_path.is_file() and schem_path.is_file()):
        return None

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    build_id = build_dir.name

    compatibility = stats.get("compatibility")
    if not isinstance(compatibility, dict):
        compatibility = {
            "valid": None,
            "status": "legacy-unchecked",
            "unknown_blocks": [],
            "invalid_states": [],
        }

    profile = stats.get("server_profile")
    if not isinstance(profile, dict):
        profile = {
            "source": "legacy",
            "minecraft_version": None,
            "data_version": None,
        }

    return {
        "id": build_id,
        "name": stats.get("name") or _display_name(build_id),
        "render": (build_dir / "render.png").relative_to(root.parent).as_posix(),
        "schem": (build_dir / "final.schem").relative_to(root.parent).as_posix(),
        "stats": (build_dir / "stats.json").relative_to(root.parent).as_posix(),
        "blueprint": (
            (build_dir / "blueprint.py").relative_to(root.parent).as_posix()
            if (build_dir / "blueprint.py").is_file()
            else None
        ),
        "dims": stats.get("dims"),
        "block_count": stats.get("block_count"),
        "namespaces": stats.get("namespaces", {}),
        "top_materials": stats.get("top_materials", []),
        "server_profile": profile,
        "compatibility": compatibility,
    }


def generate_index(root: str | Path = "generated") -> dict[str, Any]:
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)

    builds = []
    for build_dir in sorted(path for path in root_path.iterdir() if path.is_dir()):
        entry = _entry(root_path, build_dir)
        if entry is not None:
            builds.append(entry)

    manifest = {
        "version": INDEX_VERSION,
        "repository": "misterblaecher/GabCon-BuildAI",
        "builds": builds,
    }
    (root_path / "index.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
