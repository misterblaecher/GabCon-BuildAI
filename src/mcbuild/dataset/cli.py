"""Command-line interface for Minecraft dataset sourcing."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from mcbuild.dataset.pipeline import DatasetPipeline
from mcbuild.dataset.registry import SourceRegistry

app = typer.Typer(
    add_completion=False,
    help="Source, normalize and deduplicate Minecraft build datasets.",
)
console = Console()
DEFAULT_DATA_DIR = Path("data")
DataDirOption = Annotated[Path, typer.Option("--data-dir")]


def _registry() -> SourceRegistry:
    return SourceRegistry.load()


@app.command("list-sources")
def list_sources() -> None:
    registry = _registry()
    table = Table("Source", "Catalog id", "Type", "Adapter")
    for spec in registry.specs:
        table.add_row(
            spec.source_id,
            spec.catalog_id,
            spec.source_type,
            "yes" if spec.supported else "-",
        )
    console.print(table)


@app.command("source")
def source_command(
    source_name: str | None = typer.Argument(
        None,
        help="Source id/alias, for example hack337 or fable.",
    ),
    all_sources: bool = typer.Option(
        False,
        "--all",
        help="Run every catalog source with an automated adapter.",
    ),
    workers: int = typer.Option(8, "--workers", min=1, max=32),
    data_dir: DataDirOption = DEFAULT_DATA_DIR,
    limit: int | None = typer.Option(
        None,
        "--limit",
        min=1,
        help="Limit discovered artifacts (useful for smoke tests).",
    ),
) -> None:
    if all_sources == (source_name is not None):
        console.print("[red]Choose exactly one source name or --all.[/red]")
        raise typer.Exit(2)

    registry = _registry()
    pipeline = DatasetPipeline(data_dir)
    specs = (
        [spec for spec in registry.specs if spec.supported]
        if all_sources
        else [registry.resolve(source_name or "")]
    )
    failures = 0
    for spec in specs:
        console.print(f"[bold]Source {spec.source_id}[/bold] — {spec.name}")
        try:
            result = pipeline.run_source(
                spec,
                registry.adapter(spec),
                workers=workers,
                limit=limit,
            )
            console.print(
                f"  discovered={result['discovered']} "
                f"downloaded={result['downloaded']} "
                f"parsed={result['parsed']} "
                f"resumed={result['already_parsed']} "
                f"failed={result['failed']}"
            )
            failures += result["failed"]
        except Exception as exc:
            failures += 1
            console.print(f"[red]  source failed: {exc}[/red]")
            if not all_sources:
                raise typer.Exit(1) from exc
    if failures:
        console.print(
            f"[yellow]Completed with {failures} recorded failure(s); "
            "other sources/items were preserved.[/yellow]"
        )


@app.command("status")
def status(data_dir: DataDirOption = DEFAULT_DATA_DIR) -> None:
    pipeline = DatasetPipeline(data_dir)
    table = Table(
        "Source",
        "discovered",
        "downloaded",
        "parsed",
        "unique",
        "failed",
    )
    for row in pipeline.manifest.status_rows():
        table.add_row(
            str(row["source"]),
            str(row["discovered"] or 0),
            str(row["downloaded"] or 0),
            str(row["parsed"] or 0),
            str(row["unique_count"] or 0),
            str(row["failed"] or 0),
        )
    console.print(table)


@app.command("dedup")
def dedup(data_dir: DataDirOption = DEFAULT_DATA_DIR) -> None:
    pipeline = DatasetPipeline(data_dir)
    duplicates = pipeline.manifest.recompute_duplicates()
    count = pipeline.manifest.write_jsonl(
        pipeline.manifest_dir / "structures.jsonl"
    )
    console.print(
        f"Recomputed global rotation dedup: {duplicates} duplicate(s), "
        f"{count} manifest record(s)."
    )


@app.command("stats")
def stats(data_dir: DataDirOption = DEFAULT_DATA_DIR) -> None:
    pipeline = DatasetPipeline(data_dir)
    rows = list(pipeline.manifest.iter_manifest())
    structures = len(rows)
    unique = sum(1 for row in rows if row["duplicate_of"] is None)
    blocks = sum(int(row["block_count"]) for row in rows)
    volume = sum(int(row["volume"]) for row in rows)
    console.print(
        f"structures={structures:,} unique={unique:,} "
        f"non_air_blocks={blocks:,} total_volume={volume:,}"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
