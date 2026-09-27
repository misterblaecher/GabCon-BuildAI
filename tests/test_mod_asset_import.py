import io
import json
import zipfile

import pytest
from PIL import Image

from mcbuild import palette
from mcbuild.mod_asset_import import ModAssetImportError, import_mod_assets
from mcbuild.mod_assets import scan_mod_directory, write_manifest
from mcbuild.render import blockmodel, blockstate, textures


def _png_bytes(rgb=(120, 130, 140)):
    image = Image.new("RGBA", (16, 16), rgb + (255,))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _write_create_jar(path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/neoforge.mods.toml",
            """
[[mods]]
modId="create"
version="6.0.10"
displayName="Create"
""",
        )
        archive.writestr(
            "assets/create/blockstates/andesite_casing.json",
            json.dumps({"variants": {"": {"model": "create:block/andesite_casing"}}}),
        )
        archive.writestr(
            "assets/create/models/block/andesite_casing.json",
            json.dumps(
                {
                    "parent": "minecraft:block/cube_all",
                    "textures": {"all": "create:block/andesite_casing"},
                }
            ),
        )
        archive.writestr(
            "assets/create/textures/block/andesite_casing.png",
            _png_bytes(),
        )


@pytest.fixture(autouse=True)
def reset_render_asset_cache():
    yield
    blockmodel.configure_mod_asset_cache(None)
    palette._texture_derived_color.cache_clear()


def test_imported_mod_assets_are_resolved_by_renderer(tmp_path):
    mods = tmp_path / "mods"
    mods.mkdir()
    _write_create_jar(mods / "create-test.jar")

    index = scan_mod_directory(mods)
    index_path = write_manifest(index, tmp_path / "mod-assets-index.json")
    cache = tmp_path / "resourcepack"

    result = import_mod_assets(index_path, cache)

    assert result["imported_resource_count"] == 3
    assert result["namespaces"] == ["create"]
    assert result["conflict_count"] == 0
    assert (cache / "assets/create/blockstates/andesite_casing.json").is_file()
    assert (cache / "assets/create/models/block/andesite_casing.json").is_file()
    assert (cache / "assets/create/textures/block/andesite_casing.png").is_file()

    blockmodel.configure_mod_asset_cache(cache)
    palette._texture_derived_color.cache_clear()

    texture = textures.get_face_texture("create:andesite_casing", "side")
    assert texture is not None
    assert texture.size == (16, 16)

    parts = blockstate.resolve_parts("create:andesite_casing", {})
    assert parts is not None
    assert parts[0].model == "create:block/andesite_casing"

    mesh = blockmodel.get_block_mesh("create:andesite_casing", ())
    assert mesh is not None
    assert len(mesh) == 6
    assert {face.texture for face in mesh} == {"create:block/andesite_casing"}

    resolved = palette._resolve("create:andesite_casing")
    assert resolved is not None
    assert resolved[0] == (120, 130, 140)


def test_import_rejects_jar_changed_since_scan(tmp_path):
    mods = tmp_path / "mods"
    mods.mkdir()
    jar = mods / "create-test.jar"
    _write_create_jar(jar)

    index = scan_mod_directory(mods)
    index_path = write_manifest(index, tmp_path / "mod-assets-index.json")

    with zipfile.ZipFile(jar, "a") as archive:
        archive.writestr("changed-after-scan.txt", "changed")

    with pytest.raises(ModAssetImportError, match="JAR changed since the scan"):
        import_mod_assets(index_path, tmp_path / "resourcepack")


def test_import_replaces_stale_cache_contents(tmp_path):
    mods = tmp_path / "mods"
    mods.mkdir()
    _write_create_jar(mods / "create-test.jar")

    index = scan_mod_directory(mods)
    index_path = write_manifest(index, tmp_path / "mod-assets-index.json")
    cache = tmp_path / "resourcepack"
    stale = cache / "assets/old/textures/block/stale.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")

    import_mod_assets(index_path, cache)

    assert not stale.exists()
    assert (cache / "assets/create/textures/block/andesite_casing.png").is_file()
