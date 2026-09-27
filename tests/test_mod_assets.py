import json
import zipfile

from mcbuild.mod_assets import scan_mod_directory, write_manifest


def _write_jar(path, files, neoforge_toml=None):
    with zipfile.ZipFile(path, "w") as archive:
        if neoforge_toml is not None:
            archive.writestr("META-INF/neoforge.mods.toml", neoforge_toml)
        for name, data in files.items():
            archive.writestr(name, data)


def test_scan_mod_directory_indexes_render_assets_and_mod_metadata(tmp_path):
    mods = tmp_path / "mods"
    mods.mkdir()
    _write_jar(
        mods / "create-test.jar",
        {
            "assets/create/blockstates/andesite_casing.json": "{}",
            "assets/create/models/block/andesite_casing.json": "{}",
            "assets/create/textures/block/andesite_casing.png": b"png",
            "assets/create/textures/block/belt.png.mcmeta": "{}",
            "assets/create/lang/en_us.json": "{}",
        },
        neoforge_toml="""
[[mods]]
modId="create"
version="6.0.10"
displayName="Create"
""",
    )

    manifest = scan_mod_directory(mods)

    assert manifest["jar_count"] == 1
    assert manifest["scanned_jar_count"] == 1
    assert manifest["error_count"] == 0
    assert manifest["namespace_providers"] == {"create": ["create-test.jar"]}
    assert manifest["totals"]["blockstates"] == 1
    assert manifest["totals"]["block_models"] == 1
    assert manifest["totals"]["block_textures"] == 1
    assert manifest["totals"]["block_texture_meta"] == 1
    assert manifest["totals"]["render_assets"] == 4

    jar = manifest["jars"][0]
    assert jar["mods"] == [{"id": "create", "version": "6.0.10", "display_name": "Create"}]
    assert len(jar["sha256"]) == 64
    assert jar["total_asset_files"] == 5

    assets = jar["namespaces"]["create"]
    assert assets["blockstates"] == ["assets/create/blockstates/andesite_casing.json"]
    assert assets["block_models"] == ["assets/create/models/block/andesite_casing.json"]
    assert assets["block_textures"] == ["assets/create/textures/block/andesite_casing.png"]
    assert assets["block_texture_meta"] == ["assets/create/textures/block/belt.png.mcmeta"]


def test_scan_records_multiple_providers_for_same_namespace(tmp_path):
    mods = tmp_path / "mods"
    mods.mkdir()
    _write_jar(
        mods / "addon.jar",
        {"assets/create/models/block/addon_part.json": "{}"},
    )
    _write_jar(
        mods / "create.jar",
        {"assets/create/blockstates/andesite_casing.json": "{}"},
    )

    manifest = scan_mod_directory(mods)

    assert manifest["namespace_providers"]["create"] == ["addon.jar", "create.jar"]


def test_bad_jar_is_reported_without_aborting_scan(tmp_path):
    mods = tmp_path / "mods"
    mods.mkdir()
    (mods / "broken.jar").write_bytes(b"not a zip")
    _write_jar(mods / "valid.jar", {"assets/example/blockstates/test.json": "{}"})

    manifest = scan_mod_directory(mods)

    assert manifest["jar_count"] == 2
    assert manifest["scanned_jar_count"] == 1
    assert manifest["error_count"] == 1
    assert manifest["errors"][0]["file"] == "broken.jar"
    assert manifest["namespace_providers"] == {"example": ["valid.jar"]}


def test_write_manifest_creates_parent_directory(tmp_path):
    manifest = {
        "format_version": 1,
        "mods_dir": "mods",
        "jar_count": 0,
        "scanned_jar_count": 0,
        "error_count": 0,
        "namespace_count": 0,
        "namespace_providers": {},
        "totals": {},
        "jars": [],
        "errors": [],
    }

    output = write_manifest(manifest, tmp_path / "cache" / "mod-assets-index.json")

    assert json.loads(output.read_text(encoding="utf-8")) == manifest
