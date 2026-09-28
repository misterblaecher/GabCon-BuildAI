"""Canonical block-state and coordinate normalization."""

from __future__ import annotations

from collections.abc import Iterable

from mcbuild.dataset.models import CanonicalBlock, CanonicalStructure

AIR_IDS = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def canonical_block_state(raw: str) -> str:
    """Canonicalize namespace/property ordering without discarding any properties."""
    text = raw.strip()
    if not text:
        raise ValueError("Block state must not be empty.")

    if text.endswith("]") and "[" in text:
        base, raw_props = text.split("[", 1)
        prop_text = raw_props[:-1]
    else:
        base, prop_text = text, ""

    base = base.strip()
    if ":" not in base:
        base = f"minecraft:{base}"
    namespace, path = base.split(":", 1)
    namespace, path = namespace.strip(), path.strip()
    if not namespace or not path:
        raise ValueError(f"Invalid block id: {raw!r}")

    props: list[tuple[str, str]] = []
    if prop_text:
        for part in prop_text.split(","):
            key, sep, value = part.partition("=")
            key, value = key.strip(), value.strip()
            if not sep or not key or not value:
                raise ValueError(f"Invalid block-state property in {raw!r}: {part!r}")
            props.append((key, value))

    if not props:
        return f"{namespace}:{path}"
    rendered = ",".join(f"{key}={value}" for key, value in sorted(props))
    return f"{namespace}:{path}[{rendered}]"


def normalize_structure(
    blocks: Iterable[tuple[int, int, int, str]],
    *,
    dimensions: tuple[int, int, int] | None = None,
    minecraft_version: str | None = None,
    metadata: dict | None = None,
    include_air: bool = False,
) -> CanonicalStructure:
    """Translate the occupied bounding box to origin and deterministically sort blocks.

    When ``dimensions`` is supplied it is preserved exactly, while coordinates are still
    translated by their minimum observed coordinate. This is important for source formats
    whose declared bounds intentionally contain empty border cells.
    """
    normalized_input: list[tuple[int, int, int, str]] = []
    for x, y, z, state in blocks:
        if not all(isinstance(value, int) for value in (x, y, z)):
            raise ValueError("Block coordinates must be integers.")
        canonical = canonical_block_state(state)
        if include_air or canonical.split("[", 1)[0] not in AIR_IDS:
            normalized_input.append((x, y, z, canonical))

    if not normalized_input:
        raise ValueError("Structure contains no non-air blocks.")

    minx = min(row[0] for row in normalized_input)
    miny = min(row[1] for row in normalized_input)
    minz = min(row[2] for row in normalized_input)
    maxx = max(row[0] for row in normalized_input)
    maxy = max(row[1] for row in normalized_input)
    maxz = max(row[2] for row in normalized_input)

    occupied_dimensions = (maxx - minx + 1, maxy - miny + 1, maxz - minz + 1)
    if dimensions is None:
        dimensions = occupied_dimensions
    elif any(not isinstance(value, int) or value <= 0 for value in dimensions):
        raise ValueError(f"Invalid declared dimensions: {dimensions!r}")
    elif any(occupied > declared for occupied, declared in zip(occupied_dimensions, dimensions, strict=True)):
        raise ValueError(
            f"Occupied bounds {occupied_dimensions!r} exceed declared dimensions {dimensions!r}."
        )

    canonical_blocks = tuple(
        sorted(
            (
                CanonicalBlock(x - minx, y - miny, z - minz, state)
                for x, y, z, state in normalized_input
            ),
            key=lambda block: (block.x, block.y, block.z, block.state),
        )
    )
    return CanonicalStructure(
        blocks=canonical_blocks,
        dimensions=dimensions,
        minecraft_version=minecraft_version,
        metadata=dict(metadata or {}),
    )
