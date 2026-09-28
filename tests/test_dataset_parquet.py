from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from mcbuild.dataset.formats.parquet import FarhanParquetReader
from mcbuild.dataset.hashing import structure_hashes
from mcbuild.dataset.normalize import normalize_structure_with_state_ids


def _write_farhan_fixture(path: Path, *, empty: bool = False) -> None:
    voxel_ids = [0] * 32768
    voxel_names = ["air"] * 32768
    if not empty:
        voxel_ids[0] = 1
        voxel_names[0] = "stone"
        flat_index = 1 * 32 * 32 + 2 * 32 + 3
        voxel_ids[flat_index] = 1572
        voxel_names[flat_index] = "oak_stairs"
    table = pa.table(
        {
            "title": ["fixture house"],
            "subtitle": ["Land Structure Map"],
            "description": ["fixture description"],
            "tags": ['["house", "oak"]'],
            "url": ["https://www.planetminecraft.com/project/fixture"],
            "voxel_data": [voxel_ids],
            "voxel_name_data": [voxel_names],
        }
    )
    pq.write_table(table, path)


def test_farhan_parquet_stream_preserves_opaque_state_ids(tmp_path: Path):
    path = tmp_path / "data_with_voxel_names.parquet"
    _write_farhan_fixture(path)

    record = next(FarhanParquetReader().iter_records(path, limit=1))
    assert record.error is None
    assert record.source_item_id == "row:000000"
    assert record.minecraft_version == "1.16.4"
    assert record.tags == ("house", "oak")
    assert record.structure is not None
    assert record.structure.dimensions == (32, 32, 32)
    assert record.structure.block_count == 2
    by_state = {block.state: block for block in record.structure.blocks}
    assert by_state["minecraft:stone"].source_state_id == 1
    assert by_state["minecraft:oak_stairs"].source_state_id == 1572
    payload = record.structure.to_dict()
    assert [0, 0, 0, 1] in payload["source_state_ids"]
    assert payload["metadata"]["opaque_block_state_ids"] is True


def test_farhan_empty_record_is_reported_not_raised(tmp_path: Path):
    path = tmp_path / "data_with_voxel_names.parquet"
    _write_farhan_fixture(path, empty=True)

    record = next(FarhanParquetReader().iter_records(path))
    assert record.structure is None
    assert record.error == "Structure contains no non-air blocks."


def test_opaque_state_id_participates_in_exact_hash():
    first = normalize_structure_with_state_ids(
        [(0, 0, 0, "oak_stairs", 100)],
        dimensions=(32, 32, 32),
    )
    second = normalize_structure_with_state_ids(
        [(0, 0, 0, "oak_stairs", 101)],
        dimensions=(32, 32, 32),
    )
    assert structure_hashes(first).structure_hash != structure_hashes(second).structure_hash
