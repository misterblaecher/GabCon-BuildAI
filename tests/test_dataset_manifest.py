from pathlib import Path

from mcbuild.dataset.hashing import structure_hashes
from mcbuild.dataset.manifest import ManifestDB
from mcbuild.dataset.models import SourceItem
from mcbuild.dataset.normalize import normalize_structure


def _item(source_item_id: str) -> SourceItem:
    return SourceItem(
        source="fixture",
        source_item_id=source_item_id,
        source_url=f"https://example.invalid/{source_item_id}",
        download_url=f"https://example.invalid/{source_item_id}",
        source_file=f"{source_item_id}.schem",
        lineage_dataset="fixture",
    )


def test_manifest_resume_and_global_rotation_dedup(tmp_path: Path):
    db = ManifestDB(tmp_path / "manifests" / "downloads.sqlite")
    item_a = _item("a")
    item_b = _item("b")
    for item in (item_a, item_b):
        db.upsert_item(item)
        raw = tmp_path / item.source_file
        raw.write_bytes(b"fixture")
        db.mark_downloaded(
            item,
            raw_path=raw,
            sha256="abcd",
            size=7,
        )

    structure = normalize_structure(
        [
            (0, 0, 0, "stone"),
            (1, 0, 0, "oak_stairs[facing=north]"),
        ]
    )
    hashes = structure_hashes(structure)
    db.mark_parsed(
        item_a,
        structure=structure,
        hashes=hashes,
        canonical_path=tmp_path / "a.json.gz",
    )
    db.mark_parsed(
        item_b,
        structure=structure,
        hashes=hashes,
        canonical_path=tmp_path / "b.json.gz",
    )

    rows = list(db.iter_manifest())
    assert len(rows) == 2
    assert rows[0]["duplicate_of"] is None
    assert rows[1]["duplicate_of"] == rows[0]["build_id"]
    status = db.status_rows()[0]
    assert status["discovered"] == 2
    assert status["parsed"] == 2
    assert status["unique_count"] == 1
