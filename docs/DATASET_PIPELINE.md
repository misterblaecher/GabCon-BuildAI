# Dataset sourcing pipeline

GabCon BuildAI includes a resumable dataset ingestion path exposed as `mcbuild-dataset`.
The machine-readable source catalogue in `docs/dataset_sources.json` remains the authority
for source identity, provenance, lineage, and double-counting warnings.

## Commands

```bash
uv run mcbuild-dataset list-sources
uv run mcbuild-dataset source hack337 --workers 8
uv run mcbuild-dataset source farhanwew --workers 4
uv run mcbuild-dataset source fable --workers 8
uv run mcbuild-dataset status
uv run mcbuild-dataset dedup
uv run mcbuild-dataset stats
```

Use `--data-dir` to keep a corpus outside the repository and `--limit` for smoke tests.
The default `data/` directory is ignored by Git.

## Storage layout

```text
data/
├── raw/<source>/...                 original downloaded bytes
├── extracted/<source>/...           safe archive extraction
├── canonical/<source>/<hash>.json.gz
├── manifests/downloads.sqlite       resumable state + errors + hashes
├── manifests/structures.jsonl       portable provenance manifest
└── cache/
```

Raw files are never replaced by the canonical representation. Downloads use `.part` files,
HTTP Range resumption when supported, size/hash checks when upstream metadata exposes them,
and atomic rename after validation. ZIP/TAR extraction rejects paths that escape the target
directory and ignores link entries.

## Canonical structure

The canonical representation is sparse and keeps declared source dimensions. It does not
force builds into a 32³ cube. Each block keeps its complete block-state string when the
source format provides it.

The pipeline computes three hashes:

- `structure_hash`: exact normalized coordinates + block state;
- `rotation_hash`: canonical minimum across four Y-axis rotations, including directional
  property rotation for common Minecraft states;
- `occupancy_hash`: coordinates only, useful for detecting recolors/material substitutions.

Mirror equivalence is intentionally not part of the default deduplication rule.

For Farhan/rom1504-derived Parquet, the public mapping collapses multiple numeric block-state
IDs to the same block name. The importer therefore preserves each original 1.16.4 numeric
state ID as opaque provenance and includes it in the exact hash instead of inventing missing
properties.

## Supported readers

- Sponge Schematic v2/v3 (`.schem`)
- Litematica (`.litematic`)
- vanilla Minecraft structure NBT (`.nbt`)
- Hack337 blueprint JSON
- ZIP/TAR/TGZ containers
- Farhan/rom1504-derived `data_with_voxel_names.parquet`

The source registry can enumerate additional public repositories/datasets from the catalogue,
but a catalogue entry is not automatically equivalent to a verified canonical importer.
Datasets that expose research tensors/chunks, website-only downloads, or undocumented binary
formats should remain catalogue-only until their format and provenance can be mapped without
loss.

## Verified real-source smoke tests

The branch implementation was exercised against live public artifacts in GitHub Actions:

| Source | Scope used | Result |
| --- | --- | --- |
| Hack337/Minecraft-Schematics | one remote artifact | 1 discovered, 1 downloaded, 1 parsed, 1 unique, 0 failed |
| farhanwew/minecraft-schematics-dataset | one Parquet row | 1 discovered, 1 downloaded, 1 parsed, 1 unique, 0 failed |
| TheAIdude303/Minecraft-Fable-Schem-final | first selected archive | 1,001 tracked items, 979 parsed, 963 unique, 21 recorded failures |

Fable is intentionally a failure-isolation test as well as an ingestion test: malformed or
unsupported members are recorded in SQLite while valid members continue through the run.

## Source priorities and current treatment

The catalogue remains broader than the verified importers:

- **Hack337**: verified native schematic importer.
- **Farhan / rom1504 lineage**: verified Parquet importer; dense 32³ is retained as source
  geometry rather than promoted to the project-wide master representation.
- **Fable**: verified archive/native schematic ingestion.
- **3D-Craft / HouseCraft**: catalogued as a valuable sequential voxel/order prior; not treated
  as a native schematic corpus without a loss-aware format adapter.
- **MineAnyBuild**: catalogued primarily as a multimodal planning benchmark; raw-data lineage
  includes GrabCraft-derived material and should not be counted blindly as independent builds.
- **DreamCubed Human/Natural**: catalogued as chunk datasets; chunks are not counted as whole
  buildings.
- **schematic-diffusion external corpus**: repository documents an external ~120k-file archive,
  but the archive is not committed to GitHub. It remains an explicit external/manual source
  until provenance and download behavior can be validated reliably.

This distinction is deliberate: the pipeline should fail honestly or leave a source
catalogue-only rather than fabricate dimensions, state properties, authorship, or uniqueness.

## Failure and resume semantics

A source item advances through discovered/downloaded/parsed states in SQLite. Errors are
recorded per item and per stage. Re-running the same command reuses completed local files and
parsed rows when their recorded paths still exist.

For archive or container sources, child structures receive their own manifest rows and
canonical hashes. Global deduplication is recomputed after a source run and can also be
re-run explicitly with `mcbuild-dataset dedup`.

## Development checks

```bash
uv run ruff check src/mcbuild/dataset tests/test_dataset_*.py
uv run ruff format --check src/mcbuild/dataset tests/test_dataset_*.py
uv run pytest tests/test_dataset_*.py
```

The normal repository CI still runs the complete project lint/format/test suite. The manual
`Dataset sourcing smoke` workflow additionally exercises live public sources and is kept
separate so routine PR CI does not depend on third-party dataset availability.
