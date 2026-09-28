"""Structure readers for source formats supported by the dataset pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from mcbuild.dataset.formats.blueprint import BlueprintJsonReader
from mcbuild.dataset.formats.litematic import LitematicReader
from mcbuild.dataset.formats.nbt import MinecraftStructureReader
from mcbuild.dataset.formats.parquet import FarhanParquetReader
from mcbuild.dataset.formats.schem import SpongeSchemReader
from mcbuild.dataset.models import CanonicalStructure


class StructureReader(Protocol):
    def can_read(self, path: Path) -> bool: ...

    def read(self, path: Path) -> CanonicalStructure: ...


class ContainerStructureReader(Protocol):
    def can_read(self, path: Path) -> bool: ...


READERS: tuple[StructureReader, ...] = (
    SpongeSchemReader(),
    LitematicReader(),
    MinecraftStructureReader(),
    BlueprintJsonReader(),
)
CONTAINER_READERS: tuple[ContainerStructureReader, ...] = (FarhanParquetReader(),)


def reader_for(path: Path) -> StructureReader | None:
    return next((reader for reader in READERS if reader.can_read(path)), None)


def container_reader_for(path: Path) -> ContainerStructureReader | None:
    return next((reader for reader in CONTAINER_READERS if reader.can_read(path)), None)


def read_structure(path: Path) -> CanonicalStructure:
    reader = reader_for(path)
    if reader is None:
        raise ValueError(f"Unsupported structure format: {path.name}")
    return reader.read(path)
