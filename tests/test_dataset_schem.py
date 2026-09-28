from pathlib import Path

from mcbuild.dataset.formats import read_structure
from mcbuild.dataset.hashing import structure_hashes
from mcbuild.dataset.manifest import ManifestDB
from mcbuild.dataset.models import SourceItem
from mcbuild.export.schem import export_schem
from mcbuild.palette import get_block
from mcbuild.voxel import VoxelGrid


def test_schem_to_canonical_hash_manifest_end_to_end(tmp_path: Path):
    grid = VoxelGrid()
    grid.set(10, 3, -2, get_block("stone").index)
    grid.set(
        11,
        3,
        -2,
        get_block("oak_stairs[facing=north,half=bottom,shape=straight]").index,
    )
    source_path = tmp_path / "fixture.schem"
    export_schem(grid, str(source_path))

    structure = read_structure(source_path)
    assert structure.dimensions == (2, 1, 1)
    assert structure.blocks[0].x == 0
    assert structure.blocks[1].x == 1
    assert "facing=north" in structure.blocks[1].state

    hashes = structure_hashes(structure)
    assert hashes.structure_hash.startswith("sha256:")
    assert hashes.rotation_hash.startswith("sha256:")

    item = SourceItem(
        source="fixture",
        source_item_id="fixture.schem",
        source_url="https://example.invalid/fixture.schem",
        download_url="https://example.invalid/fixture.schem",
        source_file="fixture.schem",
        lineage_dataset="fixture",
    )
    db = ManifestDB(tmp_path / "manifest.sqlite")
    db.upsert_item(item)
    db.mark_downloaded(
        item,
        raw_path=source_path,
        sha256="fixture",
        size=source_path.stat().st_size,
    )
    canonical = tmp_path / "canonical.json.gz"
    db.mark_parsed(
        item,
        structure=structure,
        hashes=hashes,
        canonical_path=canonical,
    )
    row = next(db.iter_manifest())
    assert row["block_count"] == 2
    assert row["dimensions_json"] == "[2, 1, 1]"
