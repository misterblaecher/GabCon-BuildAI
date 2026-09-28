"""Reader for dense Farhan/rom1504-derived voxel Parquet records."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from mcbuild.dataset.models import CanonicalStructure
from mcbuild.dataset.normalize import normalize_structure_with_state_ids


@dataclass(frozen=True, slots=True)
class ParquetStructureRecord:
    source_item_id: str
    source_url: str | None
    title: str | None
    description: str | None
    tags: tuple[str, ...]
    minecraft_version: str | None
    structure: CanonicalStructure | None
    metadata: dict[str, Any]
    error: str | None = None


def _tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return (value,)
        if isinstance(decoded, list):
            return tuple(str(item) for item in decoded)
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return (str(value),)


class FarhanParquetReader:
    """Stream rows instead of materializing all 8,328 dense structures at once."""

    minecraft_version = "1.16.4"

    def can_read(self, path: Path) -> bool:
        return path.name == "data_with_voxel_names.parquet"

    def iter_records(self, path: Path, *, limit: int | None = None) -> Iterator[ParquetStructureRecord]:
        parquet = pq.ParquetFile(path)
        available = set(parquet.schema_arrow.names)
        required = {"voxel_data", "voxel_name_data"}
        missing = required - available
        if missing:
            raise ValueError(f"Farhan Parquet is missing required columns: {sorted(missing)}")

        preferred = [
            "title",
            "subtitle",
            "description",
            "tags",
            "url",
            "downloadLink",
            "finalDownloadLink",
            "voxel_data",
            "voxel_name_data",
        ]
        columns = [name for name in preferred if name in available]
        produced = 0
        row_index = 0
        for batch in parquet.iter_batches(batch_size=16, columns=columns):
            rows = batch.to_pydict()
            for local_index in range(batch.num_rows):
                if limit is not None and produced >= limit:
                    return
                voxel_ids = rows["voxel_data"][local_index]
                voxel_names = rows["voxel_name_data"][local_index]
                values = {name: rows[name][local_index] for name in columns if name not in required}
                invalid_lengths = len(voxel_ids) != 32768 or len(voxel_names) != 32768

                blocks: list[tuple[int, int, int, str, int]] = []
                if not invalid_lengths:
                    for flat_index, (state_id, name) in enumerate(
                        zip(voxel_ids, voxel_names, strict=True)
                    ):
                        state_id = int(state_id)
                        if state_id == 0 or name is None or str(name) in {"air", "minecraft:air"}:
                            continue
                        x = flat_index // (32 * 32)
                        remainder = flat_index % (32 * 32)
                        y = remainder // 32
                        z = remainder % 32
                        blocks.append((x, y, z, str(name), state_id))
                original_url = str(values.get("url")) if values.get("url") else None
                metadata = {
                    "format": "farhan_parquet",
                    "row_index": row_index,
                    "subtitle": values.get("subtitle"),
                    "download_link": values.get("downloadLink"),
                    "final_download_link": values.get("finalDownloadLink"),
                    "opaque_block_state_ids": True,
                    "block_state_id_version": self.minecraft_version,
                }
                error = None
                if invalid_lengths:
                    structure = None
                    error = (
                        f"Farhan row {row_index} has invalid voxel lengths: "
                        f"ids={len(voxel_ids)} names={len(voxel_names)}"
                    )
                else:
                    try:
                        structure = normalize_structure_with_state_ids(
                            blocks,
                            dimensions=(32, 32, 32),
                            minecraft_version=self.minecraft_version,
                            metadata=metadata,
                        )
                    except ValueError as exc:
                        structure = None
                        error = str(exc)
                yield ParquetStructureRecord(
                    source_item_id=f"row:{row_index:06d}",
                    source_url=original_url,
                    title=str(values.get("title")) if values.get("title") else None,
                    description=(
                        str(values.get("description")) if values.get("description") else None
                    ),
                    tags=_tags(values.get("tags")),
                    minecraft_version=self.minecraft_version,
                    structure=structure,
                    metadata=metadata,
                    error=error,
                )
                produced += 1
                row_index += 1
