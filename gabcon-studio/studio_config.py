"""Shared local Studio settings. The engine's VoxelGrid limit is four million blocks."""
from __future__ import annotations

import os

ENGINE_MAX_BLOCKS = 4_000_000
DEFAULT_STUDIO_MAX_BLOCKS = 1_000_000
DETAILED_PREVIEW_MAX_BLOCKS = 160_000
BROWSER_SURFACE_MAX_BLOCKS = 30_000
# The current Sponge exporter builds a dense volume in memory, even for sparse builds.
MAX_SCHEMATIC_VOLUME = 20_000_000


def studio_block_limit() -> int:
    """Return the configured Studio cap, never exceeding the mcbuild engine cap."""
    raw = os.getenv("GABCON_STUDIO_MAX_BLOCKS", str(DEFAULT_STUDIO_MAX_BLOCKS))
    try:
        requested = int(raw.strip().replace("_", ""))
    except (ValueError, AttributeError):
        return DEFAULT_STUDIO_MAX_BLOCKS
    return min(ENGINE_MAX_BLOCKS, max(1, requested))

def studio_preview_mode() -> str:
    """Auto = detailed on small builds, fast = always render top-down."""
    return "fast" if os.getenv("GABCON_STUDIO_PREVIEW_MODE", "").strip().lower() == "fast" else "auto"
