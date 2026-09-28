"""Core models used by the dataset sourcing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True, order=True)
class CanonicalBlock:
    """One normalized Minecraft block, preserving its complete block-state string."""

    x: int
    y: int
    z: int
    state: str
    source_state_id: int | str | None = None

    def as_row(self) -> list[int | str]:
        return [self.x, self.y, self.z, self.state]


@dataclass(frozen=True, slots=True)
class CanonicalStructure:
    """Sparse canonical structure with a bounding box rooted at (0, 0, 0)."""

    blocks: tuple[CanonicalBlock, ...]
    dimensions: tuple[int, int, int]
    minecraft_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def volume(self) -> int:
        width, height, length = self.dimensions
        return width * height * length

    @property
    def palette_size(self) -> int:
        return len({(block.state, block.source_state_id) for block in self.blocks})

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "dimensions": list(self.dimensions),
            "block_count": self.block_count,
            "palette_size": self.palette_size,
            "minecraft_version": self.minecraft_version,
            "blocks": [block.as_row() for block in self.blocks],
            "metadata": self.metadata,
        }
        source_state_ids = [
            [block.x, block.y, block.z, block.source_state_id]
            for block in self.blocks
            if block.source_state_id is not None
        ]
        if source_state_ids:
            payload["source_state_ids"] = source_state_ids
        return payload


@dataclass(frozen=True, slots=True)
class SourceItem:
    """A remotely discoverable source artifact before it is downloaded."""

    source: str
    source_item_id: str
    source_url: str
    download_url: str
    source_file: str
    title: str | None = None
    description: str | None = None
    tags: tuple[str, ...] = ()
    minecraft_version: str | None = None
    expected_size: int | None = None
    expected_sha256: str | None = None
    lineage_dataset: str | None = None
    lineage_parent: str | None = None
    images: tuple[str, ...] = ()
    container: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: Path
    sha256: str
    size: int
    resumed: bool


@dataclass(frozen=True, slots=True)
class StructureHashes:
    structure_hash: str
    rotation_hash: str
    occupancy_hash: str
