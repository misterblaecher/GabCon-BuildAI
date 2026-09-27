# Generated Artifacts

This directory is used for local or CI-generated Minecraft build artifacts.

## Build a blueprint locally

From the repository root:

```bash
uv sync
uv run python tools/build_blueprint.py blueprints/01-central-portal.py
```

No OpenRouter key is required. The script executes the sandboxed mcbuild DSL directly.

By default the portal output is written to:

```text
generated/01-central-portal/
├── blueprint.py
├── render.png
├── final.schem
└── stats.json
```

Use another output directory or seed when needed:

```bash
uv run python tools/build_blueprint.py blueprints/01-central-portal.py --seed 42 --out generated/portal-v2
```

## Build from GitHub Actions

Open the repository's **Actions** tab, choose **Build Minecraft Blueprint**, then choose
**Run workflow**. The default input builds `blueprints/01-central-portal.py`.

The workflow uploads a downloadable artifact containing the render, schematic, stats and
a copy of the blueprint source.
