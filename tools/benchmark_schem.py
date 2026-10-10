"""Benchmark the local Sponge schematic exporter with a reproducible test build.

From the repository root:
    uv run python tools/benchmark_schem.py --width 64 --height 32 --length 64

No external services are contacted. Timings are machine-specific; compare runs
before/after changes on the same PC rather than assuming a fixed speedup.
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from mcbuild.export.schem import export_schem
from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid


def main() -> None:
    parser = argparse.ArgumentParser(description="GabCon-BuildAI local schematic benchmark")
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--length", type=int, default=64)
    args = parser.parse_args()
    sizes = (args.width, args.height, args.length)
    if any(size <= 0 or size > 256 for size in sizes) or args.width * args.height * args.length > 2_000_000:
        parser.error("Choose dimensions from 1 to 256, up to 2 million voxels.")

    grid = VoxelGrid()
    material = get_block("stone_bricks").index
    start = time.perf_counter()
    for y in range(args.height):
        for z in range(args.length):
            for x in range(args.width):
                grid.set(x, y, z, material)
    construction_s = time.perf_counter() - start

    with tempfile.TemporaryDirectory(prefix="gabcon-benchmark-") as directory:
        output = Path(directory) / "benchmark.schem"
        start = time.perf_counter()
        export_schem(grid, str(output))
        export_s = time.perf_counter() - start
        compressed_bytes = output.stat().st_size

    print(f"Blocks:            {len(grid):,}")
    print(f"Grid construction: {construction_s:.3f}s")
    print(f"Sponge export:     {export_s:.3f}s")
    print(f"Exported file:     {compressed_bytes:,} bytes")
    print("Note: these timings depend on CPU, storage, Python version, and palette.")


if __name__ == "__main__":
    main()
