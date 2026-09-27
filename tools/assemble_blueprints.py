#!/usr/bin/env python3
"""Assemble several mcbuild blueprints into one final WorldEdit schematic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from mcbuild import palette
from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import export_schem
from mcbuild.profile import resolve_registry_path
from mcbuild.render.views import build_contact_sheet
from mcbuild.validation import validate_structural_blocks
from mcbuild.voxel import VoxelGrid

DEFAULT_VIEWS = [
    {"yaw": 0},
    {"yaw": 1},
    {"yaw": 2},
    {"yaw": 3},
    {"mode": "top-down"},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble multiple mcbuild blueprint modules into one schematic."
    )
    parser.add_argument("layout", type=Path, help="JSON layout describing blueprint paths and offsets.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Server block-registry JSON. Defaults to MCBUILD_SERVER_REGISTRY.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Base deterministic seed.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Override output directory from the layout JSON.",
    )
    return parser.parse_args()


def _module_bounds(grid: VoxelGrid, offset: tuple[int, int, int]):
    if grid.bounds is None:
        return None
    (minx, miny, minz), (maxx, maxy, maxz) = grid.bounds
    ox, oy, oz = offset
    return [[minx + ox, miny + oy, minz + oz], [maxx + ox, maxy + oy, maxz + oz]]


def assemble(layout_path: Path, registry: Path | None, seed: int, out_override: Path | None) -> dict:
    data = json.loads(layout_path.read_text(encoding="utf-8"))

    registry_path = resolve_registry_path(registry)
    if registry_path is not None:
        palette.configure_server_registry(registry_path)
    else:
        palette.configure_server_profile(None)

    out_dir = out_override or Path(data.get("output", "generated/00-full-valley"))
    out_dir.mkdir(parents=True, exist_ok=True)

    master = VoxelGrid()
    modules_report: list[dict] = []
    collision_count = 0

    for index, module in enumerate(data["modules"]):
        if not module.get("enabled", True):
            continue

        name = str(module["name"])
        path = Path(module["blueprint"])
        if not path.is_file():
            raise FileNotFoundError(f"Module {name!r} blueprint not found: {path}")

        raw_offset = module.get("offset", [0, 0, 0])
        if len(raw_offset) != 3:
            raise ValueError(f"Module {name!r} offset must contain [x, y, z].")
        offset = tuple(int(v) for v in raw_offset)
        ox, oy, oz = offset

        local = VoxelGrid()
        source = path.read_text(encoding="utf-8")
        run_blueprint(source, local, seed=seed + index)

        module_collisions = 0
        for (x, y, z), palette_index in local.items():
            target = (x + ox, y + oy, z + oz)
            if target in master:
                module_collisions += 1
            master.set(*target, palette_index)

        collision_count += module_collisions
        modules_report.append(
            {
                "name": name,
                "blueprint": str(path),
                "offset": list(offset),
                "blocks": len(local),
                "bounds": _module_bounds(local, offset),
                "collisions_overwritten": module_collisions,
            }
        )

    if len(master) == 0:
        raise RuntimeError("The layout contains no enabled modules or all modules were empty.")

    validate_structural_blocks(master)

    render_path = out_dir / "render.png"
    schem_path = out_dir / "final.schem"
    stats_path = out_dir / "stats.json"

    sheet, labels, stats = build_contact_sheet(master, DEFAULT_VIEWS)
    sheet.save(render_path)
    export_schem(master, str(schem_path))

    metadata = {
        "layout": str(layout_path),
        "views": labels,
        "server_profile": palette.registry_metadata(),
        "modules": modules_report,
        "collisions_overwritten": collision_count,
        "compatibility": {"valid": True, "unknown_blocks": [], "invalid_states": []},
        **stats,
    }
    stats_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "render": render_path,
        "schem": schem_path,
        "stats": stats_path,
        "metadata": metadata,
    }


def main() -> int:
    load_dotenv()
    args = parse_args()

    try:
        result = assemble(args.layout, args.registry, args.seed, args.out)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    meta = result["metadata"]
    dims = "x".join(str(v) for v in meta["dims"])
    print(f"Modules: {len(meta['modules'])}")
    print(f"Dimensions: {dims}")
    print(f"Blocks: {meta['block_count']:,}")
    print(f"Overwritten overlaps: {meta['collisions_overwritten']:,}")
    print(f"Render: {result['render']}")
    print(f"Schematic: {result['schem']}")
    print(f"Stats: {result['stats']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
