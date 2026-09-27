# mcbuild

**Turn a sentence into a Minecraft build.** A from-scratch LLM agent that writes
a blueprint program in a sandboxed Python DSL, interprets it into voxel data,
renders labeled multi-view screenshots with a pure-software isometric renderer,
and lets a vision-capable LLM iterate via tool calls. With a concept reference,
a separate preflight vision pass extracts a persistent ReferenceSpec and a fresh
independent critic compares high-resolution reference/build views after each edit
— until it produces a WorldEdit-ready `.schem` file, or (via a NeoForge
mod + WebSocket server) builds live inside a running Minecraft world.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![uv](https://img.shields.io/badge/managed%20with-uv-de5fe9)
![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-8a2be2)
![Ollama](https://img.shields.io/badge/LLM-Ollama-black)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![Multi-view isometric render of an agent-built mansion](docs/images/mansion-hero.png)

*Four rotations of a mansion built end-to-end from the prompt `"make a mansion"` —
one of the agent's own self-critique renders, unedited.*

## How it works

```
prompt ──▶ optional reference image ──▶ vision preflight ──▶ ReferenceSpec
   │                                                     │
   └──────────────────────────────▶ builder LLM ◀────────┘
                                      │ writes blueprint (sandboxed Python DSL)
                                      ▼
                                 sparse voxel grid
                                      │
                                      ▼
                               separate native renders
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
             compact contact sheet              independent vision critic
               (CLI display)                 (fresh context + reference)
                                                        │
                                                        ▼
                              builder edits / queries / finishes ──▶ .schem
```

## Examples

Unedited iso-view renders from the agent's own run directories under `runs/`:

<table>
<tr>
<td align="center" width="33%">
<img src="docs/images/example-shrine.png" alt="A traditional Japanese shrine with a torii gate"><br>
<sub><code>"a traditional japanese shrine with a torii gate"</code></sub>
</td>
<td align="center" width="33%">
<img src="docs/images/example-castle.png" alt="A medieval castle"><br>
<sub><code>"a medival castle"</code></sub>
</td>
<td align="center" width="33%">
<img src="docs/images/example-oasis.png" alt="A small lake in a desert"><br>
<sub><code>"a small lake in a desert"</code></sub>
</td>
</tr>
</table>

## Install

```bash
uv sync --extra dev
```

Choose an LLM backend in `.env`.

**OpenRouter (default):**

```bash
cp .env.example .env
# edit .env and set:
OPENROUTER_API_KEY=...
```

**Ollama (local or another machine on your LAN):**

```dotenv
MCBUILD_LLM_BACKEND=ollama
MCBUILD_BASE_URL=http://OLLAMA_HOST_IP:11434/v1
MCBUILD_API_KEY=ollama
```

The Ollama host must listen on the LAN (for example `OLLAMA_HOST=0.0.0.0:11434`)
and TCP port 11434 must be allowed by the host firewall. Install a vision/tool-capable
model on that host, for example:

```bash
ollama pull qwen3.5:9b
```

Then run mcbuild with that Ollama model id:

```bash
uv run mcbuild "a medieval watchtower with interior spiral stairs" --model qwen3.5:9b --reasoning off
```

For Qwen 3.5 on Ollama, mcbuild explicitly disables reasoning on turns that expose
tools. This keeps Ollama's OpenAI-compatible response in structured `tool_calls`
instead of allowing the model to print a tool-shaped JSON object as normal assistant
text. Vision input and the independent reference critic still use the same
OpenAI-compatible `/v1/chat/completions` endpoint.


## Usage

```bash
uv run mcbuild "a medieval watchtower with interior spiral stairs"
```

<details>
<summary><strong>All options</strong></summary>

```
mcbuild PROMPT
  --model TEXT                 Vision-capable model id for the configured LLM backend [default: anthropic/claude-sonnet-5]
  --max-iters INTEGER          [default: 6]
  --seed INTEGER                [default: 0]
  --display TEXT                auto|sixel|ansi|off  [default: auto]
  --out TEXT                    Run directory base  [default: runs]
  --reference/--no-reference    Generate a concept-reference image first  [default: no-reference]
  --ref-model TEXT              [default: openai/gpt-image-2]
  --reasoning TEXT              off|low|medium|high  [default: medium]
  --critic-model TEXT           ReferenceSpec/critic model; defaults to --model
  --critic-reasoning TEXT       off|low|medium|high  [default: medium]
  --reference-max-side INTEGER  Model-facing reference max edge [default: 1024]
  --critic-view-max-side INTEGER Separate render max edge [default: 768]
  --stream/--no-stream          Stream reasoning/completion text live  [default: stream]
  --cost-ceiling FLOAT          Abort (keeping the best build so far) once usage cost reaches this many USD
  --registry TEXT               Exported server block registry JSON (or MCBUILD_SERVER_REGISTRY)
```

`--display auto` probes the terminal for sixel support (via a DA1 query) and
falls back to ANSI half-block rendering (`rich-pixels`) if unavailable.

</details>

Each run writes to `runs/<timestamp>-<slug>/`:

```
prompt.txt
reference.png          (if --reference; original generated concept)
reference_model.png     (model-facing reference, max edge 1024 by default)
reference_spec.json     (persistent architectural decomposition)
iter_NN/blueprint.py
iter_NN/render.png      (compact contact sheet for display)
iter_NN/view_01.png     (native individual render; more view_NN files as requested)
iter_NN/critic.json     (independent reference critic, when a reference is active)
iter_NN/stats.json
final.schem
final_blueprint.py
session.json            (full message log, for debugging)
```

### Offline demo (no API key / no network)

```bash
uv run mcbuild "a tiny stone hut" --fake-llm --max-iters 3
```

Runs the full pipeline against a scripted stand-in LLM (broken blueprint ->
line-mapped error -> fixed blueprint -> render -> finish) so you can see the
whole loop and artifact layout without hitting the network.

## Live building in Minecraft

Instead of (or alongside) a `.schem` file, mcbuild can build directly inside a running
world: a NeoForge mod adds a `/build <prompt>` command that streams the same agent loop
over a WebSocket, placing blocks live near the player as each iteration succeeds.

Start the server:

```bash
uv run mcbuild-server --model anthropic/claude-sonnet-5 --max-iters 8
```

<details>
<summary><strong>All options</strong></summary>

```
mcbuild-server
  --host TEXT           [default: 127.0.0.1]
  --port INTEGER        [default: 8765]
  --model TEXT          Vision-capable model id for the configured LLM backend [default: anthropic/claude-sonnet-5]
  --max-iters INTEGER   [default: 6]
  --reasoning TEXT      off|low|medium|high  [default: medium]
  --cost-ceiling FLOAT  Abort a build (keeping its best build so far) once usage cost reaches this many USD
  --registry TEXT       Exported server block registry JSON (or MCBUILD_SERVER_REGISTRY)
```

These apply server-wide to every `/build` that connects — the mod only sends the prompt.

</details>

Build and run the mod (`mod/`, a NeoForge 1.21.1 project):

```bash
cd mod
./gradlew runClient   # or runServer; or `./gradlew build` and drop the jar in a world's mods/
```

Then in-game: `/build a small stone hut`. Chat shows each tool call's design notes,
per-iteration build stats, and per-turn cost as the agent works; blocks appear near the
player as each iteration succeeds. Only one build runs at a time, and there's no
authentication by design — this targets a local/trusted world, not a public server.
Run artifacts (`runs/<timestamp>-<slug>/`, including `final.schem`) are still written
for debugging, same as the CLI.

### Export the real server block registry

The NeoForge mod can export the block registry that is actually loaded by the running
server, including mod namespaces and every valid block-state combination. Run as an
operator (permission level 2+):

```text
/mcbuild registry export
```

The command writes:

```text
config/mcbuild/server-block-registry.json
```

The export contains each canonical block ID (for example `minecraft:stone` or
`create:andesite_casing`), its namespace/path, allowed property values, default state,
and the full list of valid states exposed by Minecraft. This file is intended to become
the source of truth for BuildAI server profiles instead of relying on a version-agnostic
bundled block list.

Point BuildAI at that file once (recommended via `.env` on the machine running mcbuild):

```dotenv
MCBUILD_SERVER_REGISTRY=A:\\MinecraftServer\\config\\mcbuild\\server-block-registry.json
```

or per command:

```powershell
uv run mcbuild "a Create workshop" --registry "A:\\MinecraftServer\\config\\mcbuild\\server-block-registry.json"
uv run python tools/build_blueprint.py blueprints/01-central-portal.py --registry "A:\\MinecraftServer\\config\\mcbuild\\server-block-registry.json"
```

When a server profile is active, unknown blocks, invalid state-property names, invalid
property values, and invalid state combinations are rejected before the schematic is
written. Successful generated builds record the Minecraft/DataVersion profile and
compatibility result in `stats.json`.

Blocks whose live registry exposes `half=lower|upper` are treated as true double-height
structures when using `tools/build_blueprint.py`. Both halves must be placed explicitly.
For example, a Waystone should be authored as:

```python
set_block(2, 1, 4, "waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]")
set_block(2, 2, 4, "waystones:waystone[facing=north,half=upper,origin=player,waterlogged=false]")
```

This prevents WorldEdit/Minecraft neighbor updates from removing an orphaned half after paste.

BuildAI also validates horizontal paired structures such as beds (`part=foot|head`) using
their `facing` direction. Structural validation now runs in the schematic exporter itself,
so CLI builds, agent builds, live-server builds, and direct blueprint builds all share the
same guard.

You can audit the full live registry for structural state patterns:

```powershell
uv run mcbuild-audit-structures
```

The command writes `.mcbuild/structural-blocks.json` and separates patterns into:

- `validated`: placement semantics are known and enforced. This includes vertical
  `half=lower|upper` pairs, beds, Create belts, chain drives/adjustable gearshifts,
  gantry shafts, mechanical pistons, stickers, and vanilla piston heads;
- `manual_review`: a newly installed or unknown block exposes a structural-looking
  state pattern that BuildAI does not yet know how to interpret safely.

For the current GabCon 1.21.1 registry, the previously identified nine manual-review
cases are covered explicitly. Create `state=moving` mechanical pistons are rejected
because that state requires a live moving contraption rather than a static schematic,
while Sticker `extended=true` is accepted without a companion block because Create
renders that extension from the Sticker block itself.

This makes newly installed mods visible to the audit automatically instead of relying on
a broad hard-coded allowlist while still encoding reviewed semantics for special state
machines.

### Global registry compatibility lab

After the structural audit is clean, generate a paste-test covering every loaded modded
block plus a focused vanilla geometry/BlockEntity fixture set:

```powershell
uv run mcbuild-global-test
```

The command reads `MCBUILD_SERVER_REGISTRY`, builds safe representative states, expands
known paired structures (doors/Waystones, beds, belts, etc.), validates the complete grid,
and writes:

```text
generated/03-global-registry-lab/
  supports.schem
  final.schem
  render.png
  layout.json
  stats.json
```

`layout.json` maps every tested registry block ID to its test-cell coordinates and records
states that the preview renderer cannot currently display. Flowing fluid blocks
(`level=0..15`) and non-build air variants such as `cave_air`/`void_air` are skipped
deliberately.

The lab also builds survival fixtures for blocks that cannot exist standalone: Create hand
cranks, valve handles and Redstone Links are mounted on a solid face; Haunted/Peculiar
Bells use their floor attachment; Andesite/Brass Tunnels sit on a cased horizontal belt;
Steam Whistles sit on a Fluid Tank; Gantry Carriages get a compatible Gantry Shaft;
Nozzles get an Encased Fan; and vanilla/Create rails use a flat `north_south` state.
Waystones prefer `origin=player`; Warp Plates are annotated in `layout.json` because an
Attuned Shard can be a normal placement/setup side effect rather than evidence that the
block broke.

For exhaustive vanilla testing, common survival substrates are also selected automatically:
dirt for flowers/saplings, farmland for crops, Soul Sand for Nether Wart, matching Nylium
for Nether fungi/roots, Mycelium for mushrooms, water for Lily Pads, ceiling support for
Spore Blossoms, and wall support for Tripwire Hooks.

Paste the generated lab in **two phases** so Minecraft never receives a fragile block before
its support exists. Copy both schematics to WorldEdit, then paste them at the exact same
clipboard origin/position:

```text
//schem load 03-global-registry-lab-supports
//paste -a
//schem load 03-global-registry-lab
//paste -a
```

The second schematic contains the complete build as before; the first is only a support
pre-pass that prevents neighbor updates from breaking rails, plants and attached Create
blocks during WorldEdit's placement sequence.

#### Accepted lab exceptions

A real GabCon 1.21.1 WorldEdit paste of the two-phase global lab still produced a small
set of item drops. These are documented as accepted compatibility-lab exceptions rather
than blockers for the general BuildAI schematic pipeline:

```text
Pumpkin Seeds
Melon Seeds
Azalea
Big Dripleaf
Cocoa Beans
Lily of the Valley
Amethyst Shard
Bamboo
Chorus Fruit
Cactus
Sugar Cane
Pointed Dripstone
Attuned Shard
Flowering Azalea
```

Most of these blocks/items have growth, substrate, attachment, or special initialization
semantics that are outside the current generic registry-only fixture model. The Attuned
Shard is already annotated as an expected Warp Plate setup side effect. Future fixture
work can narrow this list further without changing the structural-validation guarantees
or the normal schematic export path.

The default scope is all non-`minecraft` registry blocks plus a vanilla fixture suite for
stairs/slabs/walls, doors/beds, redstone, pistons, signs and common BlockEntities. For an
exhaustive registry pass including all vanilla blocks:

```powershell
uv run mcbuild-global-test --all-blocks
```

Use `--no-render` when only the schematic/report is needed.

### Scan mod JAR assets

BuildAI can inventory the render-relevant assets shipped by the mods installed on the
server. On the GabCon server layout, the default directory is already:

```text
A:\MinecraftServer\mods
```

Run:

```powershell
uv run mcbuild-scan-mods
```

or specify another directory explicitly:

```powershell
uv run mcbuild-scan-mods --mods-dir "A:\MinecraftServer\mods"
```

The scanner never extracts or modifies the JARs. It opens them as ZIP archives and writes
a local manifest to:

```text
.mcbuild/mod-assets-index.json
```

For every JAR the manifest records its filename, size, SHA-256, NeoForge/Fabric mod
metadata when available, asset namespaces, and exact resource paths for:

- `assets/<namespace>/blockstates/**/*.json`
- `assets/<namespace>/models/block/**/*.json`
- `assets/<namespace>/textures/block/**/*.png`
- animated texture metadata (`*.png.mcmeta`)

It also records namespace-to-JAR providers, which is important for addons that contribute
assets to another mod's namespace. This manifest is the input for the next phase that
will import/cache those resources and teach the renderer to resolve namespaced mod assets.

Set `MCBUILD_MODS_DIR` in `.env` if the mods directory is not the default location.

Import the indexed resources into BuildAI's local resource-pack cache:

```powershell
uv run mcbuild-import-mod-assets
```

The importer verifies every indexed JAR against the SHA-256 recorded by the scanner. If a
mod was updated after the scan, it stops and asks you to re-run `mcbuild-scan-mods`
instead of mixing files from two versions. The default cache is:

```text
.mcbuild/resourcepack/
  assets/
    create/
      blockstates/
      models/block/
      textures/block/
    waystones/
    ...
```

The renderer automatically reads this cache. Namespaced blocks can therefore resolve their
real blockstate/model/texture resources, for example:

```text
create:andesite_casing
  -> assets/create/blockstates/andesite_casing.json
  -> assets/create/models/block/andesite_casing.json
  -> assets/create/textures/block/andesite_casing.png
```

Architectural shapes already understood by BuildAI (stairs, slabs, walls, panes, doors,
etc.) keep their template geometry while using mod textures. Unsupported complex models
currently fall back to one correctly textured cube rather than disappearing; exact custom
Create machinery geometry is a later renderer step.

Use `MCBUILD_MOD_ASSET_INDEX` and `MCBUILD_MOD_ASSET_CACHE` to override the default
manifest/cache paths.

### Render a blueprint without an LLM

For ChatGPT-authored, hand-authored, or training-data blueprints, use the deterministic
renderer/exporter directly. It does **not** contact OpenRouter, Ollama, or any other LLM:

```powershell
uv run mcbuild-render .\builds\chatgpt\medieval_stone_tower.py
```

By default this writes `generated/<blueprint-stem>/` containing:

```text
blueprint.py
render.png
view_01.png ...
views.json
stats.json
final.schem
```

The default view set is four isometric rotations, top-down, and two cutaways. Override it
with aliases when needed:

```powershell
uv run mcbuild-render .\builds\chatgpt\medieval_stone_tower.py \
  --views "iso0,iso2,top,cutx"
```

Blueprints committed under `builds/**/*.py` are rendered automatically by
`.github/workflows/render-blueprints.yml`. The workflow commits the generated preview,
schematic, standardized view images, and metadata back to the same branch and refreshes
`generated/index.json`. This makes the repository a deterministic bridge between an
external architect (for example ChatGPT) and the mcbuild renderer/exporter.

### Export an image-to-build training dataset

The deterministic render artifacts can be exported as a versioned JSONL dataset for
vision-language fine-tuning:

```powershell
uv run mcbuild-dataset
```

This writes `training/image_build_v1.jsonl` plus a split summary. By default, each
standardized view becomes its own VRAM-friendly sample with the exact validated DSL source
used to produce the build:

```text
one image -> prompt -> target mcbuild DSL
```

All views from the same structure still receive the same deterministic train/validation/test
split, so camera variants never leak across splits. For later multi-view experiments:

```powershell
uv run mcbuild-dataset --group-views
```

This v1 format intentionally targets DSL source; a later dataset version can target a smaller
BuildSpec/component representation without changing the renderer data source.

### Static build gallery manifest

Blueprint builds written under `generated/<build-id>/` refresh `generated/index.json`
automatically. You can also regenerate it explicitly:

```bash
uv run python tools/generate_build_index.py
```

The manifest contains preview/render paths, schematic download paths, dimensions,
block counts, namespaces, server-profile metadata, and compatibility status. It is
designed to be consumed directly by the companion `minecraft-website` static gallery.

## The blueprint DSL

Blueprints are sandboxed Python — no imports, no `_`-prefixed attribute access,
no dangerous builtins, and a line-count + wall-clock execution budget. See
[`src/mcbuild/dsl/REFERENCE.md`](src/mcbuild/dsl/REFERENCE.md) for the full
primitive/transform reference and worked examples.

## Capabilities

- **Incremental editing**: `submit_blueprint` (full rebuild), `str_replace` (find/replace against
  the accumulated blueprint source, then rerun it whole), `edit_region` (rebuild one bounding box,
  freeze the rest).
- **Bulk + detail primitives**: `set_blocks`, `weighted_block`, `scatter`, `frame`, `window_grid`.
- **`get_block(x, y, z)`**: reads back whatever the blueprint has placed at a cell so far (or
  `None`), so later code can react to earlier code — skip already-weathered cells, check a
  neighbor before placing trim, etc.
- **Block states**: `"oak_stairs[facing=north,half=top]"` etc. render with true geometry (stairs,
  slabs, walls, fences, fence gates, trapdoors, doors, panes) and export with the state suffix.
- **Free 3D camera** for `inspect` (arbitrary position + look-at, orthographic z-buffer), plus
  arbitrary/y-axis slices and a lossless text `query` tool (ASCII floor plans, point lookups,
  material histograms).
- **`'air'`** is placeable — carves/erases and is exported as `minecraft:air`.

Every build call names the views it wants back (up to 8 per build — isometric
yaws, top-down, cutaways/slices), and the self-critique render is a contact
sheet of exactly those views, with dimensions/block-count/top-materials stats
reported alongside:

![Contact sheet: iso rotations, top-down, and cutaways](docs/images/mansion-contact-sheet.png)

## Project layout

```
src/mcbuild/
  cli.py             typer CLI, rich progress feed, sixel/ANSI display
  config.py          run configuration
  voxel.py           sparse VoxelGrid
  palette.py         curated block palette + fuzzy suggestions
  rundir.py          runs/<timestamp>-<slug>/ artifact management
  dsl/                sandbox, stdlib primitives, errors, REFERENCE.md
  render/             mesh rasterizer + free camera, iso contact sheet, sixel encoder,
                      block geometry (blockmodel/blockstate), textures
  llm/                OpenAI-compatible OpenRouter/Ollama client, scripted offline FakeLLM
  agent/              orchestration loop, prompts, tool schemas, text query views
  export/             Sponge Schematic v3 (.schem) export
  server/             mcbuild-server WebSocket entry point, live-build session + grid diffing

mod/                  NeoForge 1.21.1 mod: /build command, WebSocket client, block placement
```

## Development

```bash
uv run pytest              # tests
uv run ruff check .        # lint
uv run ruff format .       # format
uv run ty check            # type check
```

Tests cover: sandbox security (imports/dunders/budget), DSL shape primitives,
palette lookup + suggestions, isometric renderer output, sixel encoding,
Sponge Schematic v2 round-trip via `nbtlib`, and an offline agent-loop
integration test (scripted LLM: error -> fix -> finish) via the CLI's
`--fake-llm` path.

CI runs all four (lint, format check, type check, tests) on every push/PR.

## Notes / limitations

- Accurate geometry covers the core architectural shape families; other stateful blocks fall
  back to full cubes, and blocks with no resolvable texture (e.g. `air`, `barrier`) don't render.
- Block geometry is paired from bundled vanilla blockstate JSON + hardcoded shape templates
  (the vanilla model JSONs are not shipped); silhouettes are correct, not pixel-exact-vanilla.
- No cross-run memory / few-shot retrieval of past builds.
- Live building (`mod/` + `mcbuild-server`) is NeoForge-only, single-build-at-a-time, and has
  no authentication — meant for a local/trusted world, not a public server.

## Future work (backlog)

- A structured plan/component-registry tool and gating `finish()` on a verification checklist.
- Iteration diffs (blocks added/removed vs. the previous iteration) and richer stats
  (per-storey counts, interior air volume, mirror-symmetry score).

## Acknowledgments

This project was inspired by [*APT: Architectural Planning and Text-to-Blueprint
Construction Using Large Language Models for Open-World Agents*](https://arxiv.org/pdf/2411.17255)
(Chen & Gao, 2024), which explores LLM-driven blueprint construction for
Minecraft agents. mcbuild is an independent, from-scratch implementation and
is not affiliated with or derived from that paper's code.

## AI disclosure

This project was built with significant AI assistance (Claude): most of the
codebase, this README, and much of the iterative design work were written or
co-written by an LLM agent under human direction and review. The renders
throughout this README are unedited output from the agent described above,
not hand-picked or touched-up examples.

## License

[MIT](LICENSE), except for the bundled Minecraft block textures/blockstates —
see [`src/mcbuild/assets/NOTICE.md`](src/mcbuild/assets/NOTICE.md). Minecraft
is a trademark of Mojang Studios / Microsoft; this project is not affiliated
with or endorsed by them.
