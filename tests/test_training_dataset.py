import json
from pathlib import Path

from mcbuild.training_dataset import _split_for_id, export_dataset


def _write_complete_build(root: Path, build_id: str) -> None:
    build = root / build_id
    build.mkdir(parents=True)
    (build / "blueprint.py").write_text("set_block(0, 0, 0, 'stone_bricks')\n", encoding="utf-8")
    (build / "final.schem").write_bytes(b"schem")
    (build / "view_01.png").write_bytes(b"png")
    (build / "view_02.png").write_bytes(b"png")
    (build / "views.json").write_text(
        json.dumps(
            [
                {"file": "view_01.png", "label": "yaw 0deg", "spec": {"yaw": 0}},
                {"file": "view_02.png", "label": "top-down", "spec": {"mode": "top-down"}},
            ]
        ),
        encoding="utf-8",
    )
    (build / "stats.json").write_text(
        json.dumps(
            {
                "dims": [1, 1, 1],
                "block_count": 1,
                "namespaces": {"minecraft": 1},
                "top_materials": [["stone_bricks", 1]],
            }
        ),
        encoding="utf-8",
    )


def test_export_dataset_writes_jsonl_with_grouped_views(tmp_path: Path):
    generated = tmp_path / "generated"
    _write_complete_build(generated, "tower-a")
    _write_complete_build(generated, "tower-b")

    output = tmp_path / "training" / "dataset.jsonl"
    counts = export_dataset(generated, output, repository_root=tmp_path)

    lines = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert counts["total"] == 4
    assert len(lines) == 4

    first = lines[0]
    assert first["task"] == "image_to_mcbuild_dsl"
    assert len(first["images"]) == 1
    assert first["images"][0].startswith("generated/")
    assert "set_block" in first["target"]
    assert first["split"] == _split_for_id(first["metadata"]["source_build_id"])

    tower_a = [sample for sample in lines if sample["metadata"]["source_build_id"] == "tower-a"]
    assert len(tower_a) == 2
    assert len({sample["split"] for sample in tower_a}) == 1

    summary = json.loads(output.with_suffix(".summary.json").read_text(encoding="utf-8"))
    assert summary["counts"]["total"] == 4


def test_split_is_stable_per_build_id():
    assert _split_for_id("same-build") == _split_for_id("same-build")


def test_export_dataset_can_group_views(tmp_path: Path):
    generated = tmp_path / "generated"
    _write_complete_build(generated, "tower-a")
    output = tmp_path / "training" / "grouped.jsonl"

    counts = export_dataset(generated, output, repository_root=tmp_path, group_views=True)

    sample = json.loads(output.read_text(encoding="utf-8").strip())
    assert counts["total"] == 1
    assert len(sample["images"]) == 2
    assert sample["id"] == "tower-a"
