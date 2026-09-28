from mcbuild.dataset.registry import SourceRegistry


def test_catalog_drives_primary_source_adapters():
    registry = SourceRegistry.load()
    assert (
        registry.resolve("hack337").catalog_id
        == "hack337-minecraft-schematics"
    )
    assert (
        registry.resolve("farhanwew").catalog_id
        == "farhanwew-minecraft-schematics-dataset"
    )
    assert (
        registry.resolve("fable").catalog_id
        == "minecraft-fable-schem-final"
    )
    assert (
        registry.adapter(registry.resolve("hack337")).source_id
        == "hack337"
    )
