from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcbuild.render_cli import _parse_views, app, render_blueprint_file

runner = CliRunner()


def test_render_blueprint_file_writes_complete_artifacts(tmp_path: Path):
    blueprint = tmp_path / "tower.py"
    blueprint.write_text(
        "\n".join(
            [
                "cylinder(0, 0, 0, height=8, r=3, block='stone_bricks', hollow=True)",
                "floor(-2, -2, 2, 2, 0, 'oak_planks')",
                "clear(-1, 1, -3, 1, 2, -3)",
                "cone(0, 0, 8, r=4, height=4, block='spruce_planks')",
            ]
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "generated" / "tower"

    stats = render_blueprint_file(
        blueprint,
        out_dir,
        seed=7,
        view_names="iso0,iso2,top,cutx",
    )

    assert stats["block_count"] > 0
    assert stats["seed"] == 7
    assert len(stats["views"]) == 4
    assert (out_dir / "blueprint.py").read_text(encoding="utf-8") == blueprint.read_text(encoding="utf-8")
    assert (out_dir / "render.png").is_file()
    assert (out_dir / "view_01.png").is_file()
    assert (out_dir / "views.json").is_file()
    assert (out_dir / "stats.json").is_file()
    assert (out_dir / "final.schem").is_file()
    assert (out_dir.parent / "index.json").is_file()


def test_parse_views_rejects_unknown_alias():
    with pytest.raises(ValueError, match="Unknown view"):
        _parse_views("iso0,sideways")


def test_render_cli_entrypoint(tmp_path: Path):
    blueprint = tmp_path / "simple.py"
    blueprint.write_text("set_block(0, 0, 0, 'stone_bricks')", encoding="utf-8")
    out_dir = tmp_path / "artifact"

    result = runner.invoke(
        app,
        [
            str(blueprint),
            "--out",
            str(out_dir),
            "--views",
            "iso0",
            "--no-update-gallery",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Rendered:" in result.output
    assert (out_dir / "render.png").is_file()
    assert (out_dir / "final.schem").is_file()
