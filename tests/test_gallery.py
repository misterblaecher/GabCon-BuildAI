import json

from mcbuild.gallery import generate_index


def test_generate_index_collects_complete_builds(tmp_path):
    generated = tmp_path / "generated"
    build_dir = generated / "demo-build"
    build_dir.mkdir(parents=True)
    (build_dir / "render.png").write_bytes(b"png")
    (build_dir / "final.schem").write_bytes(b"schem")
    (build_dir / "blueprint.py").write_text("set_block(0,0,0,'stone')", encoding="utf-8")
    (build_dir / "stats.json").write_text(
        json.dumps(
            {
                "dims": [1, 1, 1],
                "block_count": 1,
                "namespaces": {"minecraft": 1},
                "top_materials": [["stone", 1]],
                "server_profile": {
                    "source": "server-export",
                    "minecraft_version": "1.21.1",
                    "data_version": 3955,
                },
                "compatibility": {
                    "valid": True,
                    "unknown_blocks": [],
                    "invalid_states": [],
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = generate_index(generated)

    assert manifest["version"] == 1
    assert len(manifest["builds"]) == 1
    entry = manifest["builds"][0]
    assert entry["id"] == "demo-build"
    assert entry["render"] == "generated/demo-build/render.png"
    assert entry["schem"] == "generated/demo-build/final.schem"
    assert entry["compatibility"]["valid"] is True
    assert json.loads((generated / "index.json").read_text(encoding="utf-8")) == manifest


def test_generate_index_skips_incomplete_directories(tmp_path):
    generated = tmp_path / "generated"
    incomplete = generated / "missing-schematic"
    incomplete.mkdir(parents=True)
    (incomplete / "render.png").write_bytes(b"png")
    (incomplete / "stats.json").write_text("{}", encoding="utf-8")

    manifest = generate_index(generated)

    assert manifest["builds"] == []
