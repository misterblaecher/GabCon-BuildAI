"""Runs a locally pasted mcbuild blueprint with the project's existing engine.

This script is launched in a child process by server.py. It does NOT call an LLM.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from mcbuild import palette
from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import export_schem
from mcbuild.profile import resolve_registry_path
from mcbuild.render.views import build_contact_sheet
from mcbuild.validation import validate_structural_blocks
from mcbuild.voxel import VoxelGrid

from studio_config import (
    BROWSER_SURFACE_MAX_BLOCKS,
    DETAILED_PREVIEW_MAX_BLOCKS,
    MAX_SCHEMATIC_VOLUME,
    studio_block_limit,
)

VIEWS = [
    {"yaw": 0},
    {"yaw": 1},
    {"yaw": 2},
    {"yaw": 3},
    {"mode": "top-down"},
    {"yaw": 1, "cutaway": "z"},
]
NEIGHBORS = (
    (1, 0, 0), (-1, 0, 0), (0, 1, 0),
    (0, -1, 0), (0, 0, 1), (0, 0, -1),
)


def build_surface(grid: VoxelGrid) -> dict:
    """Browser-friendly surface voxels with face bitmask; excludes interior solids."""
    renderable = set()
    color_by_index = {}
    for (x, y, z), index in grid.items():
        block = palette.get_block_by_index(index)
        if not block.renderable:
            continue
        renderable.add((x, y, z))
        color_by_index[index] = [int(v) for v in block.rgb[:3]]

    bounds = grid.bounds
    origin = list(bounds[0]) if bounds else [0, 0, 0]
    surface = []
    overflow = False
    for (x, y, z), index in grid.items():
        if (x, y, z) not in renderable:
            continue
        mask = 0
        for bit, (dx, dy, dz) in enumerate(NEIGHBORS):
            if (x + dx, y + dy, z + dz) not in renderable:
                mask |= (1 << bit)
        if not mask:
            continue
        if len(surface) >= BROWSER_SURFACE_MAX_BLOCKS:
            overflow = True
            break
        surface.append([x - origin[0], y - origin[1], z - origin[2], *color_by_index[index], mask])

    return {
        "surface": [] if overflow else surface,
        "too_large": overflow,
        "origin": origin,
        "count": len(renderable),
    }


def main() -> int:
    blueprint_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    seed = int(sys.argv[3])
    load_dotenv()
    try:
        registry = resolve_registry_path(None)
        if registry is None:
            palette.configure_server_profile(None)
        else:
            palette.configure_server_registry(registry)

        source = blueprint_path.read_text(encoding="utf-8")
        grid = VoxelGrid()
        run_blueprint(source, grid, seed=seed)
        if not len(grid):
            raise ValueError("Le code s'exécute, mais ne place aucun bloc.")
        max_blocks = studio_block_limit()
        if len(grid) > max_blocks:
            raise ValueError(
                f"Limite Studio : {max_blocks:,} blocs ; la construction en contient {len(grid):,}. "
                "Modifie GABCON_STUDIO_MAX_BLOCKS dans .env (4 000 000 maximum)."
            )
        bounds = grid.bounds
        assert bounds is not None
        dimensions = tuple(high - low + 1 for low, high in zip(bounds[0], bounds[1], strict=True))
        bounding_volume = dimensions[0] * dimensions[1] * dimensions[2]
        if bounding_volume > MAX_SCHEMATIC_VOLUME:
            raise ValueError(
                f"Volume englobant trop grand ({bounding_volume:,} cases, "
                f"limite {MAX_SCHEMATIC_VOLUME:,}). "
                "Rapproche les parties éloignées : l'exporteur .schem alloue aussi les cases vides."
            )
        validate_structural_blocks(grid)

        out_dir.mkdir(parents=True, exist_ok=True)
        # Six detailed rasterizations can be extremely expensive on a million-block build.
        # For large plans, retain all blocks in the schematic but render one top view.
        detailed_preview = len(grid) <= DETAILED_PREVIEW_MAX_BLOCKS
        preview_views = VIEWS if detailed_preview else [{"mode": "top-down"}]
        sheet, labels, stats = build_contact_sheet(grid, preview_views)
        sheet.save(out_dir / "render.png")
        export_schem(grid, str(out_dir / "final.schem"))
        if detailed_preview:
            surface = build_surface(grid)
        else:
            surface = {
                "surface": [],
                "too_large": True,
                "origin": list(bounds[0]),
                "count": len(grid),
            }
        (out_dir / "voxels.json").write_text(json.dumps(surface, separators=(",", ":")), encoding="utf-8")

        metadata = {
            "seed": seed,
            "views": labels,
            "palette_warnings": list(getattr(grid, "palette_warnings", [])),
            "server_profile": palette.registry_metadata(),
            "compatibility": {"valid": True},
            "interactive": not surface["too_large"],
            "preview_mode": "six_views" if detailed_preview else "top_down",
            "studio_block_limit": max_blocks,
            "bounding_volume": bounding_volume,
            "material_count": len({idx for _, idx in grid.items()}),
            **stats,
        }
        (out_dir / "stats.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"ok": True, "blocks": len(grid)}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
