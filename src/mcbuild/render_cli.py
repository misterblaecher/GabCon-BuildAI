"""Deterministic blueprint -> render/schematic pipeline with no LLM calls."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from mcbuild import palette
from mcbuild.dsl.errors import BlueprintError
from mcbuild.dsl.sandbox import run_blueprint
from mcbuild.export.schem import export_schem
from mcbuild.gallery import generate_index
from mcbuild.profile import ProfileError, resolve_registry_path
from mcbuild.render import views
from mcbuild.validation import BuildValidationError, validate_structural_blocks
from mcbuild.voxel import VoxelGrid

app = typer.Typer(add_completion=False)
console = Console()

_DEFAULT_VIEWS = "iso0,iso1,iso2,iso3,top,cutx,cutz"


def _parse_views(raw: str) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    aliases: dict[str, dict[str, Any]] = {
        "iso0": {"yaw": 0},
        "iso1": {"yaw": 1},
        "iso2": {"yaw": 2},
        "iso3": {"yaw": 3},
        "top": {"mode": "top-down"},
        "cutx": {"yaw": 2, "cutaway": "x"},
        "cutz": {"yaw": 1, "cutaway": "z"},
    }
    for token in (part.strip().lower() for part in raw.split(",")):
        if not token:
            continue
        spec = aliases.get(token)
        if spec is None:
            allowed = ", ".join(aliases)
            raise ValueError(f"Unknown view {token!r}. Use one of: {allowed}.")
        specs.append(dict(spec))
    if not specs:
        raise ValueError("At least one render view is required.")
    return specs


def render_blueprint_file(
    blueprint: Path,
    out_dir: Path,
    *,
    seed: int = 0,
    view_names: str = _DEFAULT_VIEWS,
    name: str | None = None,
    update_gallery: bool = True,
) -> dict[str, Any]:
    """Execute one DSL blueprint and write deterministic render/export artifacts."""
    source = blueprint.read_text(encoding="utf-8")
    view_specs = _parse_views(view_names)

    grid = VoxelGrid()
    run_blueprint(source, grid, seed=seed)
    validate_structural_blocks(grid)
    if len(grid) == 0:
        raise ValueError("Blueprint produced an empty voxel grid.")

    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(blueprint, out_dir / "blueprint.py")

    renderings, stats = views.build_renderings(grid, view_specs)
    sheet = views.compose_contact_sheet(renderings)
    sheet.save(out_dir / "render.png")

    view_manifest: list[dict[str, Any]] = []
    for index, ((label, image), spec) in enumerate(zip(renderings, view_specs, strict=True), start=1):
        filename = f"view_{index:02d}.png"
        image.save(out_dir / filename)
        view_manifest.append({"file": filename, "label": label, "spec": spec})

    export_schem(grid, str(out_dir / "final.schem"))

    stats = dict(stats)
    stats.update(
        {
            "name": name or blueprint.stem.replace("_", " ").replace("-", " ").title(),
            "source_blueprint": blueprint.as_posix(),
            "seed": seed,
            "views": view_manifest,
        }
    )
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    (out_dir / "views.json").write_text(json.dumps(view_manifest, indent=2), encoding="utf-8")

    if update_gallery and out_dir.parent.name == "generated":
        generate_index(out_dir.parent)

    return stats


@app.command()
def render(
    blueprint: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Sandboxed mcbuild DSL blueprint (.py).",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Artifact directory. Defaults to generated/<blueprint-stem>.",
    ),
    seed: int = typer.Option(0, "--seed"),
    views_arg: str = typer.Option(
        _DEFAULT_VIEWS,
        "--views",
        help="Comma-separated views: iso0,iso1,iso2,iso3,top,cutx,cutz.",
    ),
    name: str | None = typer.Option(None, "--name", help="Display name stored in stats/gallery metadata."),
    registry: str | None = typer.Option(
        None,
        "--registry",
        help="Server block-registry JSON. Defaults to MCBUILD_SERVER_REGISTRY.",
    ),
    update_gallery: bool = typer.Option(
        True,
        "--update-gallery/--no-update-gallery",
        help="Refresh generated/index.json when the output lives under generated/.",
    ),
) -> None:
    """Render/export a blueprint without invoking any LLM."""
    registry_path = resolve_registry_path(registry)
    if registry_path is not None:
        try:
            palette.configure_server_registry(registry_path)
        except ProfileError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(2) from exc
    else:
        palette.configure_server_profile(None)

    out_dir = out or Path("generated") / blueprint.stem
    try:
        stats = render_blueprint_file(
            blueprint,
            out_dir,
            seed=seed,
            view_names=views_arg,
            name=name,
            update_gallery=update_gallery,
        )
    except (BlueprintError, BuildValidationError, ValueError, OSError) as exc:
        console.print(f"[red]Render failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    dims = stats.get("dims")
    dims_text = "x".join(str(v) for v in dims) if dims else "unknown"
    console.print(
        f"[green]Rendered:[/green] {out_dir / 'render.png'}  "
        f"dims={dims_text}  blocks={stats.get('block_count', 0)}"
    )
    console.print(f"[green]Schematic:[/green] {out_dir / 'final.schem'}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
