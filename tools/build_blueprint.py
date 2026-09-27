#!/usr/bin/env python3
"""Execute an mcbuild DSL blueprint without an LLM and export preview artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import export_schem
from mcbuild.render.views import build_contact_sheet
from mcbuild.voxel import VoxelGrid

DEFAULT_VIEWS = [
    {"yaw": 0},
    {"yaw": 1},
    {"yaw": 2},
    {"yaw": 3},
    {"mode": "top-down"},
    {"yaw": 1, "cutaway": "z"},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an mcbuild blueprint directly, with no OpenRouter/API key."
    )
    parser.add_argument("blueprint", type=Path, help="Path to a sandboxed mcbuild blueprint .py file.")
    parser.add_argument("--seed", type=int, default=0, help="Seed used by weighted blocks/scatter.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory. Defaults to generated/<blueprint-stem>/.",
    )
    return parser.parse_args()


def build(blueprint_path: Path, out_dir: Path, seed: int) -> dict:
    blueprint_path = blueprint_path.resolve()
    if not blueprint_path.is_file():
        raise FileNotFoundError(f"Blueprint not found: {blueprint_path}")

    source = blueprint_path.read_text(encoding="utf-8")
    grid = VoxelGrid()
    run_blueprint(source, grid, seed=seed)

    if len(grid) == 0:
        raise RuntimeError("Blueprint executed successfully but produced an empty build.")

    out_dir.mkdir(parents=True, exist_ok=True)

    render_path = out_dir / "render.png"
    schem_path = out_dir / "final.schem"
    stats_path = out_dir / "stats.json"
    source_copy_path = out_dir / "blueprint.py"

    sheet, labels, stats = build_contact_sheet(grid, DEFAULT_VIEWS)
    sheet.save(render_path)
    export_schem(grid, str(schem_path))
    shutil.copy2(blueprint_path, source_copy_path)

    metadata = {
        "source": str(blueprint_path),
        "seed": seed,
        "views": labels,
        "palette_warnings": getattr(grid, "palette_warnings", []),
        **stats,
    }
    stats_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "render": render_path,
        "schem": schem_path,
        "stats": stats_path,
        "blueprint": source_copy_path,
        "metadata": metadata,
    }


def main() -> int:
    args = parse_args()
    blueprint_path: Path = args.blueprint
    out_dir = args.out or Path("generated") / blueprint_path.stem

    try:
        result = build(blueprint_path, out_dir, args.seed)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    metadata = result["metadata"]
    dims = metadata["dims"]
    dims_text = "x".join(str(value) for value in dims) if dims else "empty"

    print(f"Blueprint: {blueprint_path}")
    print(f"Dimensions: {dims_text}")
    print(f"Blocks: {metadata['block_count']:,}")
    print(f"Render: {result['render']}")
    print(f"Schematic: {result['schem']}")
    print(f"Stats: {result['stats']}")

    warnings = metadata["palette_warnings"]
    if warnings:
        print("Palette warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
