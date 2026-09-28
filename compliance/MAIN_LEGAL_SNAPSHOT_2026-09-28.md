# Main legal/compliance snapshot

Captured from `main` before legal/compliance stripping.



---

## README.md

```text
# mcbuild

**Turn a sentence into a Minecraft build.** A from-scratch LLM agent that writes
a blueprint program in a sandboxed Python DSL, interprets it into voxel data,
renders labeled multi-view screenshots with a pure-software isometric renderer,
and lets a vision-capable LLM critique its own renders and iterate via tool
calls — until it produces a WorldEdit-ready `.schem` file, or (via a NeoForge
mod + WebSocket server) builds live inside a running Minecraft world.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![uv](https://img.shields.io/badge/managed%20with-uv-de5fe9)
![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-8a2be2)
![Ollama](https://img.shields.io/badge/LLM-Ollama-black)

![Multi-view isometric render of an agent-built mansion](docs/images/mansion-hero.png)

*Four rotations of a mansion built end-to-end from the prompt `"make a mansion"` —
one of the agent's own self-critique renders, unedited.*

## How it works

``\`
prompt ──▶ LLM writes a blueprint (sandboxed Python DSL)
             │
             ▼
        DSL interpreter ──▶ sparse voxel grid
             │
             ▼
     isometric renderer ──▶ contact-sheet PNG of the views the LLM requested (rotations / top-down / cutaways)
             │
             ▼
   vision LLM critiques the render, calls a tool to edit/query/finish
             │
             └──── loop until finish() ────▶ WorldEdit .schem + full run directory
``\`

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

``\`bash
uv sync --extra dev
``\`

Choose an LLM backend in `.env`.

**OpenRouter (default):**

``\`bash
cp .env.example .env
# edit .env and set:
OPENROUTER_API_KEY=...
``\`

**Ollama (local or another machine on your LAN):**

``\`dotenv
MCBUILD_LLM_BACKEND=ollama
MCBUILD_BASE_URL=http://OLLAMA_HOST_IP:11434/v1
MCBUILD_API_KEY=ollama
``\`

The Ollama host must listen on the LAN (for example `OLLAMA_HOST=0.0.0.0:11434`)
and TCP port 11434 must be allowed by the host firewall. Install a vision/tool-capable
model on that host, for example:

``\`bash
ollama pull qwen3.5:9b
``\`

Then run mcbuild with that Ollama model id:

``\`bash
uv run mcbuild "a medieval watchtower with interior spiral stairs" --model qwen3.5:9b --reasoning off
``\`

For Qwen 3.5 on Ollama, mcbuild explicitly disables reasoning on turns that expose
tools. This is intentional: it keeps Ollama's OpenAI-compatible response in structured
`tool_calls` instead of allowing the model to print a tool-shaped JSON object as normal
assistant text. Vision input still uses the same OpenAI-compatible `/v1/chat/completions`
endpoint.

## Usage

``\`bash
uv run mcbuild "a medieval watchtower with interior spiral stairs"
``\`

<details>
<summary><strong>All options</strong></summary>

``\`
mcbuild PROMPT
  --model TEXT                 Vision-capable model id for the configured LLM backend [default: anthropic/claude-sonnet-5]
  --max-iters INTEGER          [default: 6]
  --seed INTEGER                [default: 0]
  --display TEXT                auto|sixel|ansi|off  [default: auto]
  --out TEXT                    Run directory base  [default: runs]
  --reference/--no-reference    Generate a concept-reference image first  [default: no-reference]
  --ref-model TEXT              [default: openai/gpt-image-2]
  --reasoning TEXT              off|low|medium|high  [default: medium]
  --stream/--no-stream          Stream reasoning/completion text live  [default: stream]
  --cost-ceiling FLOAT          Abort (keeping the best build so far) once usage cost reaches this many USD
  --registry TEXT               Exported server block registry JSON (or MCBUILD_SERVER_REGISTRY)
``\`

`--display auto` probes the terminal for sixel support (via a DA1 query) and
falls back to ANSI half-block rendering (`rich-pixels`) if unavailable.

</details>

Each run writes to `runs/<timestamp>-<slug>/`:

``\`
prompt.txt
reference.png          (if --reference)
iter_NN/blueprint.py
iter_NN/render.png
iter_NN/stats.json
final.schem
final_blueprint.py
session.json            (full message log, for debugging)
``\`

### Offline demo (no API key / no network)

``\`bash
uv run mcbuild "a tiny stone hut" --fake-llm --max-iters 3
``\`

Runs the full pipeline against a scripted stand-in LLM (broken blueprint ->
line-mapped error -> fixed blueprint -> render -> finish) so you can see the
whole loop and artifact layout without hitting the network.

## Live building in Minecraft

Instead of (or alongside) a `.schem` file, mcbuild can build directly inside a running
world: a NeoForge mod adds a `/build <prompt>` command that streams the same agent loop
over a WebSocket, placing blocks live near the player as each iteration succeeds.

Start the server:

``\`bash
uv run mcbuild-server --model anthropic/claude-sonnet-5 --max-iters 8
``\`

<details>
<summary><strong>All options</strong></summary>

``\`
mcbuild-server
  --host TEXT           [default: 127.0.0.1]
  --port INTEGER        [default: 8765]
  --model TEXT          Vision-capable model id for the configured LLM backend [default: anthropic/claude-sonnet-5]
  --max-iters INTEGER   [default: 6]
  --reasoning TEXT      off|low|medium|high  [default: medium]
  --cost-ceiling FLOAT  Abort a build (keeping its best build so far) once usage cost reaches this many USD
  --registry TEXT       Exported server block registry JSON (or MCBUILD_SERVER_REGISTRY)
``\`

These apply server-wide to every `/build` that connects — the mod only sends the prompt.

</details>

Build and run the mod (`mod/`, a NeoForge 1.21.1 project):

``\`bash
cd mod
./gradlew runClient   # or runServer; or `./gradlew build` and drop the jar in a world's mods/
``\`

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

``\`text
/mcbuild registry export
``\`

The command writes:

``\`text
config/mcbuild/server-block-registry.json
``\`

The export contains each canonical block ID (for example `minecraft:stone` or
`create:andesite_casing`), its namespace/path, allowed property values, default state,
and the full list of valid states exposed by Minecraft. This file is intended to become
the source of truth for BuildAI server profiles instead of relying on a version-agnostic
bundled block list.

Point BuildAI at that file once (recommended via `.env` on the machine running mcbuild):

``\`dotenv
MCBUILD_SERVER_REGISTRY=A:\\MinecraftServer\\config\\mcbuild\\server-block-registry.json
``\`

or per command:

``\`powershell
uv run mcbuild "a Create workshop" --registry "A:\\MinecraftServer\\config\\mcbuild\\server-block-registry.json"
uv run python tools/build_blueprint.py blueprints/01-central-portal.py --registry "A:\\MinecraftServer\\config\\mcbuild\\server-block-registry.json"
``\`

When a server profile is active, unknown blocks, invalid state-property names, invalid
property values, and invalid state combinations are rejected before the schematic is
written. Successful generated builds record the Minecraft/DataVersion profile and
compatibility result in `stats.json`.

Blocks whose live registry exposes `half=lower|upper` are treated as true double-height
structures when using `tools/build_blueprint.py`. Both halves must be placed explicitly.
For example, a Waystone should be authored as:

``\`python
set_block(2, 1, 4, "waystones:waystone[facing=north,half=lower,origin=player,waterlogged=false]")
set_block(2, 2, 4, "waystones:waystone[facing=north,half=upper,origin=player,waterlogged=false]")
``\`

This prevents WorldEdit/Minecraft neighbor updates from removing an orphaned half after paste.

BuildAI also validates horizontal paired structures such as beds (`part=foot|head`) using
their `facing` direction. Structural validation now runs in the schematic exporter itself,
so CLI builds, agent builds, live-server builds, and direct blueprint builds all share the
same guard.

You can audit the full live registry for structural state patterns:

``\`powershell
uv run mcbuild-audit-structures
``\`

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

``\`powershell
uv run mcbuild-global-test
``\`

The command reads `MCBUILD_SERVER_REGISTRY`, builds safe representative states, expands
known paired structures (doors/Waystones, beds, belts, etc.), validates the complete grid,
and writes:

``\`text
generated/03-global-registry-lab/
  supports.schem
  final.schem
  render.png
  layout.json
  stats.json
``\`

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

``\`text
//schem load 03-global-registry-lab-supports
//paste -a
//schem load 03-global-registry-lab
//paste -a
``\`

The second schematic contains the complete build as before; the first is only a support
pre-pass that prevents neighbor updates from breaking rails, plants and attached Create
blocks during WorldEdit's placement sequence.

#### Accepted lab exceptions

A real GabCon 1.21.1 WorldEdit paste of the two-phase global lab still produced a small
set of item drops. These are documented as accepted compatibility-lab exceptions rather
than blockers for the general BuildAI schematic pipeline:

``\`text
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
``\`

Most of these blocks/items have growth, substrate, attachment, or special initialization
semantics that are outside the current generic registry-only fixture model. The Attuned
Shard is already annotated as an expected Warp Plate setup side effect. Future fixture
work can narrow this list further without changing the structural-validation guarantees
or the normal schematic export path.

The default scope is all non-`minecraft` registry blocks plus a vanilla fixture suite for
stairs/slabs/walls, doors/beds, redstone, pistons, signs and common BlockEntities. For an
exhaustive registry pass including all vanilla blocks:

``\`powershell
uv run mcbuild-global-test --all-blocks
``\`

Use `--no-render` when only the schematic/report is needed.

### Scan mod JAR assets

BuildAI can inventory the render-relevant assets shipped by the mods installed on the
server. On the GabCon server layout, the default directory is already:

``\`text
A:\MinecraftServer\mods
``\`

Run:

``\`powershell
uv run mcbuild-scan-mods
``\`

or specify another directory explicitly:

``\`powershell
uv run mcbuild-scan-mods --mods-dir "A:\MinecraftServer\mods"
``\`

The scanner never extracts or modifies the JARs. It opens them as ZIP archives and writes
a local manifest to:

``\`text
.mcbuild/mod-assets-index.json
``\`

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

``\`powershell
uv run mcbuild-import-mod-assets
``\`

The importer verifies every indexed JAR against the SHA-256 recorded by the scanner. If a
mod was updated after the scan, it stops and asks you to re-run `mcbuild-scan-mods`
instead of mixing files from two versions. The default cache is:

``\`text
.mcbuild/resourcepack/
  assets/
    create/
      blockstates/
      models/block/
      textures/block/
    waystones/
    ...
``\`

The renderer automatically reads this cache. Namespaced blocks can therefore resolve their
real blockstate/model/texture resources, for example:

``\`text
create:andesite_casing
  -> assets/create/blockstates/andesite_casing.json
  -> assets/create/models/block/andesite_casing.json
  -> assets/create/textures/block/andesite_casing.png
``\`

Architectural shapes already understood by BuildAI (stairs, slabs, walls, panes, doors,
etc.) keep their template geometry while using mod textures. Unsupported complex models
currently fall back to one correctly textured cube rather than disappearing; exact custom
Create machinery geometry is a later renderer step.

Use `MCBUILD_MOD_ASSET_INDEX` and `MCBUILD_MOD_ASSET_CACHE` to override the default
manifest/cache paths.

### Static build gallery manifest

Blueprint builds written under `generated/<build-id>/` refresh `generated/index.json`
automatically. You can also regenerate it explicitly:

``\`bash
uv run python tools/generate_build_index.py
``\`

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

## Dataset & research sources

A maintained inventory of Minecraft build datasets, schematic collections, benchmarks,
derivative research repositories, source-site restrictions, and format/tooling references
is available in [`docs/DATASET_SOURCES.md`](docs/DATASET_SOURCES.md).

A machine-readable version for future importers, rights filtering, and lineage-aware
deduplication is available in [`docs/dataset_sources.json`](docs/dataset_sources.json).

The inventory deliberately separates **unique source builds** from mirrors/forks/derivatives
and records provenance, lineage, formats, scale, and technical suitability for GabCon.

## Project layout

``\`
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
``\`

## Development

``\`bash
uv run pytest              # tests
uv run ruff check .        # lint
uv run ruff format .       # format
uv run ty check            # type check
``\`

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


```


---

## pyproject.toml

```text
[project]
name = "mcbuild"
version = "0.1.0"
description = "Text-to-Minecraft LLM building agent"
readme = "README.md"
authors = [
    { name = "Harry Yu", email = "harryyunull@gmail.com" }
]
requires-python = ">=3.11"
dependencies = [
    "openai>=1.50.0",
    "numpy>=1.26",
    "pillow>=10.0",
    "nbtlib>=2.0",
    "rich>=13.0",
    "rich-pixels>=3.0",
    "typer>=0.12",
    "python-dotenv>=1.0",
    "websockets>=13.0",
]

[project.scripts]
mcbuild = "mcbuild.cli:main"
mcbuild-server = "mcbuild.server.ws_server:main"
mcbuild-scan-mods = "mcbuild.mod_assets:main"
mcbuild-import-mod-assets = "mcbuild.mod_asset_import:main"
mcbuild-audit-structures = "mcbuild.registry_structures:main"
mcbuild-global-test = "mcbuild.global_test_lab:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.8.0",
    "ty>=0.0.1a1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcbuild"]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.ruff.format]
quote-style = "double"

[tool.ty.environment]
python-version = "3.11"
python-platform = "all"

[tool.pytest.ini_options]
testpaths = ["tests"]

```


---

## mod/gradle.properties

```text
## Environment Properties

# The Minecraft version must agree with the NeoForge version to get properly mapped mod code
minecraft_version=1.21.1
# The Minecraft version range can use any release version of Minecraft as bounds
minecraft_version_range=[1.21.1,1.21.2)
# The NeoForge version must agree with the Minecraft version to get properly mapped mod code
neoforge_version=21.1.235
# The NeoForge version range can only use the major version of NeoForge as bounds
neoforge_version_range=[21.1,)
# The loader version range can only use the major version of FML as bounds
loader_version_range=[1,)

## Mod Properties

mod_id=mcbuild_live
mod_name=mcbuild Live
mod_license=MIT
mod_version=1.1.0
mod_group_id=com.mcbuild.mod
mod_authors=Harry Yu
mod_description=Streams mcbuild agent builds live and exports the loaded server block registry for BuildAI.

## Dependencies

# Java-WebSocket: bundled into the mod jar via jarJar since it isn't on the Minecraft/NeoForge
# classpath. See src/mcbuild/server/ws_server.py for the Python side of this connection.
java_websocket_version=1.5.7

## Gradle Properties

org.gradle.jvmargs=-Xmx3G
org.gradle.daemon=false
org.gradle.debug=false

```


---

## mod/build.gradle

```text
plugins {
    id 'eclipse'
    id 'idea'
    id 'net.neoforged.moddev' version '2.0.141'
}

version = mod_version
group = mod_group_id

base {
    archivesName = mod_id
}

java.toolchain.languageVersion = JavaLanguageVersion.of(21)

tasks.withType(JavaCompile).configureEach {
    options.encoding = 'UTF-8'
}

println "Java: ${System.getProperty 'java.version'}, JVM: ${System.getProperty 'java.vm.version'} " +
        "(${System.getProperty 'java.vendor'}), Arch: ${System.getProperty 'os.arch'}"

neoForge {
    version = neoforge_version

    runs {
        client {
            client()
        }
        server {
            server()
        }
    }

    mods {
        "${mod_id}" {
            sourceSet sourceSets.main
        }
    }
}

// Bundle Java-WebSocket into the mod jar (it isn't part of the Minecraft/NeoForge classpath).
// See gradle.properties for the version pin. `jarJar` produces the shaded `-all.jar`, which
// is the artifact that should actually be dropped into a `mods/` folder; wire it into the
// default build so `./gradlew build` produces it without an extra step.
dependencies {
    implementation(jarJar("org.java-websocket:Java-WebSocket:${java_websocket_version}"))
}

tasks.named('assemble').configure {
    dependsOn 'jarJar'
}

tasks.named('processResources', ProcessResources).configure {
    def replaceProperties = [
            minecraft_version      : minecraft_version,
            minecraft_version_range: minecraft_version_range,
            neoforge_version       : neoforge_version,
            neoforge_version_range : neoforge_version_range,
            loader_version_range   : loader_version_range,
            mod_id                 : mod_id,
            mod_name               : mod_name,
            mod_license            : mod_license,
            mod_version            : mod_version,
            mod_authors            : mod_authors,
            mod_description        : mod_description,
    ]
    inputs.properties replaceProperties
    filesMatching(['META-INF/neoforge.mods.toml']) {
        expand replaceProperties + [project: project]
    }
}

```


---

## mod/src/main/resources/META-INF/neoforge.mods.toml

```text
modLoader="javafml"
loaderVersion="${loader_version_range}"
license="${mod_license}"

[[mods]]
modId="${mod_id}"
version="${mod_version}"
displayName="${mod_name}"
authors="${mod_authors}"
description='''${mod_description}'''

[[dependencies.${mod_id}]]
    modId="neoforge"
    type="required"
    versionRange="${neoforge_version_range}"
    ordering="NONE"
    side="BOTH"

[[dependencies.${mod_id}]]
    modId="minecraft"
    type="required"
    versionRange="${minecraft_version_range}"
    ordering="NONE"
    side="BOTH"

```


---

## docs/DATASET_SOURCES.md

```text
# Minecraft build datasets and source inventory

Research snapshot: **2026-09-28**

This document tracks public datasets, schematic collections, benchmarks, derivative research repositories, format/tooling references, and source websites that are potentially useful for training or evaluating **GabCon BuildAI / mcbuild**.

The goal is not to maximize the raw number of files. The goal is to preserve:

- original structure dimensions whenever possible;
- exact block names and block states;
- original schematic files when available;
- text metadata and captions;
- provenance and author/source URLs;
- lineage information so forks and derivatives are not double-counted.



## Best candidates for GabCon

| Source | Scale | Text | Structure | Native dimensions | Images | GabCon fit |
| --- | ---: | --- | --- | --- | --- | --- |
| Hack337/Minecraft-Schematics | 669 builds / 1,338 SFT examples | Excellent | raw schematic + JSON blueprint | Yes | Can render | **Very high** |
| farhanwew/minecraft-schematics-dataset | 8,328 | Good metadata | 32^3 voxels + block names | No | up to 12 views | **Very high technically** |
| 3D-Craft / HouseCraft | 2,500 houses | Weak semantic text | sequential voxels | Partially preserved upstream | Research visuals | **High for 3D pretraining** |
| Text2MC lineage | ~11k viable builds reported by processing projects | Good metadata | H5/voxelized structures | Mixed | Derived | **High technically** |
| Minecraft-Fable-Schem-final | 6,566 native .schem entries observed | Mostly filenames | native .schem + normalized derivatives | Yes in native shard | Limited | **High technically** |
| MineAnyBuild | 4,000 benchmark tasks | Excellent instructions | executable architectures/plans | Usually bbox-native | Yes | **High for evaluation/planning** |
| Dream-Cubed Human | 1M-10M 32^3 chunks, not whole builds | Labels, not rich captions | voxel chunks | No | No | **High for voxel pretraining only** |
| KHROTU schematic-diffusion corpus | ~120k raw files claimed | filenames/labels | .schem/.litematic -> tensors | Yes before preprocessing | planned | **Very high technically, risky provenance** |
| lukeclaw/litematica-gpt | ~3,165 DSL blueprints documented | prompt + spatial rationale | DSL -> blocks/litematic | Yes logically | No | **Very high for DSL/SFT research** |
| computational-redstone | 195 components from 19 worlds | Functional labels/metadata | .litematic | Yes | some renders | **High for functional structures** |

## Source catalogue

### 1. Hack337/Minecraft-Schematics

- Dataset: https://huggingface.co/datasets/Hack337/Minecraft-Schematics
- Dataset card: https://huggingface.co/datasets/Hack337/Minecraft-Schematics/blob/main/README.md
- Reported content: raw `.schem`, `.litematic`, legacy `.schematic`, parsed JSON blueprints, mappings, and OpenAI-style SFT JSONL.
- Languages: English and Russian.
- Strength: strongest directly usable public text-to-structure seed found in this research.

### 2. rom1504/minecraft-schematics-dataset

- GitHub: https://github.com/rom1504/minecraft-schematics-dataset
- Original external dataset location referenced by the repository: https://gitlab.com/rom1504/minecraft-schematics-dataset
- Lineage root for the 8,328-record 32^3 schematic dataset used by several later repositories.
- Includes Planet Minecraft-derived metadata and TFRecord-based structure data.
- Do **not** add its count to Farhan/information-retrieval forks as if they were new builds.

### 3. farhanwew/minecraft-schematics-dataset

- GitHub: https://github.com/farhanwew/minecraft-schematics-dataset
- Parent: rom1504/minecraft-schematics-dataset.
- Verified repository artifacts include:
  - `data.parquet`
  - `data_with_voxel_names.parquet`
  - `data_with_voxel_names_multiview_image.parquet`
  - `metadata.parquet`
  - `block_state_id_to_name.json`
- Reported rows: **8,328**.
- Dense voxel shape: **32x32x32**.
- Block-state/name mapping tooling targets Minecraft **1.16.4**.
- Metadata includes title, description, tags, category, source URL and engagement fields.
- Multi-view pipeline supports up to 12 views.
- Excellent technical prototype for text/image/voxel retrieval, but original dimensions are lost by 32^3 normalization.

### 4. information-retrieval-4/minecraft-schematics-dataset-reader

- GitHub: https://github.com/information-retrieval-4/minecraft-schematics-dataset-reader
- Same 8,328-record lineage; reader/rendering/preprocessing repository.
- Treat as **tooling/derivative**, not a new independent dataset.
- Useful for Parquet reading, voxel-name conversion, multi-view rendering, retrieval metrics and point-cloud conversion.

### 5. k1a11220/minecraft-schematics-dataset

- GitHub: https://github.com/k1a11220/minecraft-schematics-dataset
- Mirror/fork of rom1504 lineage.
- No new unique build count should be assigned.

### 6. 3D-Craft / HouseCraft + VoxelCNN

- VoxelCNN GitHub: https://github.com/facebookresearch/voxelcnn
- Direct dataset archive referenced by VoxelCNN: https://craftassist.s3-us-west-2.amazonaws.com/pubr/house_data.tar.gz
- Paper: https://openaccess.thecvf.com/content_ICCV_2019/html/Chen_Order-Aware_Generative_Modeling_Using_the_3D-Craft_Dataset_ICCV_2019_paper.html
- Dataset scale reported by the paper: **2,500 houses** built from scratch by humans, including construction order.
- Excellent for learning human build ordering and spatial priors.
- Text semantics are much weaker than Hack337/MineAnyBuild.

### 7. Text2MC data-processing lineage

- GitHub: https://github.com/shauncomino/text2mc-dataprocessor
- Related model repo: https://github.com/shauncomino/text2mc_model
- Related experiment: https://github.com/hmhornung/Generative-Minecraft
- Tokenization helper: https://github.com/hmhornung/Minecraft2Token
- The processing repository contains Planet Minecraft metadata CSV files, scraping/processing code, world-to-vector tooling and H5 examples.
- Later research repositories expect `processed_builds/*.h5` plus `tok2block.json`.
- Reported secondary descriptions commonly cite about 25k downloaded projects and ~11k usable builds; verify the exact preprocessing snapshot before relying on the count.
- Strong text metadata and useful source URLs for matching and enrichment.

### 8. MineAnyBuild

- GitHub: https://github.com/MineAnyBuild/MineAnyBuild
- Hugging Face benchmark dataset: https://huggingface.co/datasets/SaDil/MineAnyBuild
- Raw-data release: https://huggingface.co/datasets/SaDil/MineAnyBuild-Raw_data
- Paper: https://arxiv.org/abs/2505.20148
- 4,000 curated spatial-planning tasks are reported by the project; this is a task count, not necessarily 4,000 unique buildings.
- Strong multi-modal natural-language instructions, stimuli and executable planning/evaluation data.
- Hugging Face release declares **CC BY-NC-SA 4.0**.

### 9. Minecraft-Fable-Schem-final

- Hugging Face: https://huggingface.co/datasets/TheAIdude303/Minecraft-Fable-Schem-final
- Research inspection found a native manifest with **6,566 .schem entries** and additional normalized/NBT/NPZ derivatives.
- Native shards are technically valuable because original schematic geometry can be preserved separately from normalized variants.
- Some naming/provenance appears related to existing public Minecraft build sites, so cross-dataset deduplication is required.

### 10. KHROTU/schematic-diffusion

- GitHub: https://github.com/KHROTU/schematic-diffusion
- Repository documents an external `Schematics.zip` corpus of roughly **120,000 raw schematic files**.
- Supports `.schem` and `.litematic` processing into tensors and text-conditioned diffusion training.

### 11. lukeclaw/litematica-gpt

- GitHub: https://github.com/lukeclaw/litematica-gpt
- Model/training notes: https://github.com/lukeclaw/litematica-gpt/blob/main/MODELS.md
- Research monorepo contains processed fine-tuning JSONL and a custom schematic DSL.
- Documentation reports about **3,165 DSL blueprints paired with synthetic spatial rationales** for representative training.
- Pipeline is highly relevant to GabCon: prompt -> planner -> compiler/DSL -> blocks.

### 12. constraint-learnability-regime-map

- GitHub: https://github.com/crabsatellite/constraint-learnability-regime-map
- Uses a unified preprocessing pipeline across Text2MC, 3D-Craft and rom1504.
- Reports **10,310 filtered builds** in one experimental pipeline.
- Valuable for:
  - unified vocabulary design;
  - VQ-VAE + autoregressive pipeline;
  - structural feature extraction;
- Treat as **derivative research**, not 10,310 new independent builds.

### 13. ms0k/voxel-vae

- GitHub: https://github.com/ms0k/voxel-vae
- Research derivative around Minecraft voxel generation / 3D-Craft lineage.
- Useful as architecture/preprocessing reference.
- Do not count underlying 3D-Craft structures again.

### 14. scaffold-diffusion

- GitHub: https://github.com/jsjung00/scaffold-diffusion
- Research derivative of 3D-Craft-style voxel data.
- Useful for generative architecture research.
- Not an independent source of unique Minecraft builds.

### 15. MineGen

- GitHub: https://github.com/Viibrant/MineGen
- Deep-learning/transformer project for Minecraft schematic generation.
- Repository includes scraping/dataset-building code but does not publish a clearly documented standalone training corpus in its README.
- Useful for pipeline and modeling references.

### 16. minecraft-schematic-generator

- GitHub: https://github.com/mmmfrieddough/minecraft-schematic-generator
- Contains world sampling, dataset compilation and model training/inference tooling.
- Does not by itself establish a clean public corpus.

### 17. computational-redstone

- GitHub: https://github.com/Rektoooooo/computational-redstone
- Repository description reports **195 components extracted from 19 published worlds**.
- Contains `.litematic` components plus manifests/tooling for functional redstone assembly.
- Valuable because it captures *functional* spatial structures rather than only architecture.

### 18. 3d-artefacts-nca

- GitHub: https://github.com/real-itu/3d-artefacts-nca
- Paper: https://arxiv.org/abs/2103.08737
- Contains NBT target structures used for Neural Cellular Automata experiments, including village/functional artefacts.
- Useful small high-quality structural corpus and for functional-machine generation research.

### 19. GDMC 2024 pre-built structures

- GitHub: https://github.com/Niels-NTG/GDMC2024
- Hand-authored pre-built structures stored as NBT plus Python behavior classes.
- Minecraft target documented as 1.20.2.
- Useful for modular/semantic structure components and composition research.
- Small corpus; not a large training dataset.

### 20. GDMC 2023 pre-built structures

- GitHub: https://github.com/Niels-NTG/GDMC2023
- Hand-authored NBT structures plus behavior/composition logic.
- Minecraft target documented as 1.19.2.
- Useful small corpus for modular settlement structure research.

### 21. silvicky/litematics

- GitHub: https://github.com/silvicky/litematics
- Public repository containing Litematica files.

### 22. Piscescup/MC-Java-Schematics

- GitHub: https://github.com/Piscescup/MC-Java-Schematics
- Public schematic collection; repository has significant binary content but limited documentation.
- Potential raw source for ingestion experiments.

### 23. minecraft-schematics-world-structures

- GitHub: https://github.com/ERGeorgiev/minecraft-schematics-world-structures
- Community archive targeting real-world structures at 1:1 scale.
- Repository currently observed with a very small number of actual `.schem` entries; includes screenshot(s) and location/context naming.
- Promising as an opt-in/community-source pattern more than as a large dataset today.

### 24. MinecraftSchematic/Schematics

- Hugging Face: https://huggingface.co/datasets/MinecraftSchematic/Schematics
- Very small release (two ZIP archives observed) with Minecraft-version-labelled builds.

### 25. Dream-Cubed Human

- Hugging Face: https://huggingface.co/datasets/dream-cubed/DreamCubedHuman
- Human-authored structures/terrain represented as **32x32x32 voxel chunks**.
- Processed release also includes natural chunks from companion data.
- This is a chunk dataset, not a whole-build corpus. Do not count chunks as unique buildings.

### 26. Dream-Cubed Natural

- Hugging Face: https://huggingface.co/datasets/dream-cubed/DreamCubedNatural
- Procedurally generated natural Minecraft chunk data referenced by Dream-Cubed Human.
- Useful for environment/terrain priors, not human-build text supervision.
- Keep separate from architectural build counts.

### 27. MiDaS

- GitHub: https://github.com/MinecraftDataset/MiDaS
- Full dataset location: https://osf.io/whgy6/
- **36,000 images across 60 block-level classes**.
- This is a perception/block-recognition dataset, not a schematic/build corpus.
- Useful for visual encoders and block recognition only.
- Do not include its image count in build counts.

### 28. CraftAssist

- GitHub: https://github.com/facebookresearch/craftassist
- Contains Minecraft assistant research, house/world data links and language/agent tooling.
- Important ecosystem reference for 3D-Craft/HouseCraft and instruction-following research.
- Do not count CraftAssist and 3D-Craft as independent build corpora unless the exact files are proven disjoint.

### 29. Generative-Minecraft

- GitHub: https://github.com/hmhornung/Generative-Minecraft
- Explicitly described as recreating Text2MC VAE results with player-build data.
- Treat as a derivative experiment, not a new dataset.
- Useful for model/tokenization experiments.

### 30. Minecraft2Token

- GitHub: https://github.com/hmhornung/Minecraft2Token
- Tokenization helper/reference for Minecraft block vocabularies.
- Not a standalone training dataset.
- Useful for vocabulary lineage checks.

## Public source websites

### Planet Minecraft

- Site: https://www.planetminecraft.com/




### GrabCraft

- Site: https://www.grabcraft.com/



### Minecraft-Schematics.com

- Site: https://www.minecraft-schematics.com/



## Tooling and format references

These are not build datasets, but they are useful to normalize imported structures without losing state information.

### Schematic AI Studio

- GitHub: https://github.com/gamerover98/Schematic-Ai-Studio
- Apache-2.0 desktop/MCP schematic editor.
- Reads/writes MCEdit `.schematic`, Sponge v2/v3 `.schem`, Litematica `.litematic`, and `.mcfunction`.
- Useful as a compatibility reference for offsets, DataVersion, BlockData, entities, ItemData and conversion-loss reporting.

### makeschem

- GitHub: https://github.com/mortie/makeschem
- Converts a simple text `x y z block_name` representation to legacy `.schematic`.
- Useful as a minimal coordinate-list interchange reference.
- Legacy-only block model; not suitable as GabCon's canonical modern representation.

### Prismarine minecraft-data

- GitHub: https://github.com/PrismarineJS/minecraft-data
- Useful for versioned block/item/protocol registries and legacy mappings.

### misode/mcmeta

- GitHub: https://github.com/misode/mcmeta
- Useful blockstate/registry metadata reference across Minecraft versions.

### Litematica

- GitHub: https://github.com/maruohon/litematica
- Reference implementation for `.litematic` behavior/version compatibility.

### litemapy

- GitHub: https://github.com/SmylerMC/litemapy
- Python parser/writer reference for Litematica schematics.

### WorldEdit / Sponge schematic references

- WorldEdit: https://github.com/EngineHub/WorldEdit
- Sponge schematic specification/history should be treated as the canonical interchange reference for GabCon's `.schem` export path.

## Lineage and deduplication graph

Do not sum rows from repositories that transform the same underlying structures.

``\`text
rom1504/minecraft-schematics-dataset
├── k1a11220 mirror/fork
├── farhanwew fork + parquet/block-name/multiview enrichment
└── information-retrieval-4 reader/renderer derivative

3D-Craft / HouseCraft
├── facebookresearch/voxelcnn
├── ms0k/voxel-vae
├── jsjung00/scaffold-diffusion
└── crabsatellite/constraint-learnability-regime-map (combined with other sources)

Text2MC lineage
├── shauncomino/text2mc-dataprocessor
├── hmhornung/Generative-Minecraft
├── hmhornung/Minecraft2Token
└── crabsatellite/constraint-learnability-regime-map (combined with other sources)
``\`

Cross-lineage duplicates are also possible because Planet Minecraft-origin structures can appear in multiple scraped/processed corpora.

## Recommended canonical GabCon record

Never make 32^3 the master representation. Keep original geometry and generate normalized views as derivatives.

``\`json
{
  "build_id": "sha256:canonical-structure-hash",
  "lineage_id": "sha256:source-lineage-hash",
  "source_dataset": "hack337",
  "source_url": "https://...",
  "source_author": "...",
  "rights_grade": "B",
  "dataset_license": "MIT",
  "build_license": null,
  "title": "Medieval Watchtower",
  "description_human": "...",
  "caption_generated": "...",
  "tags": ["tower", "medieval"],
  "minecraft_version_original": "...",
  "dimensions_original": [31, 44, 28],
  "blocks": [
    [0, 0, 0, "minecraft:stone_bricks"],
    [1, 0, 0, "minecraft:oak_stairs[facing=east,half=bottom]"]
  ],
  "source_schematic": "build.schem",
  "renders": ["view_00.png", "view_01.png"]
}
``\`

Derived artifacts may then include:

``\`text
canonical sparse structure
├── GabCon Blueprint DSL
├── dense voxel original-size
├── optional 32^3 / 64^3 crops for specific models
├── Sponge v3 .schem
├── 8-12 standardized renders
└── caption/prompt variants
``\`

## Structural deduplication

Recommended order:

1. Preserve source URL, author, original filename and upstream dataset ID.
2. Parse into canonical sparse coordinates with full block states.
3. Remove empty exterior padding and translate bounding box origin to (0,0,0).
4. Hash exact `(x,y,z,block_state)` tuples.
5. Compute canonical rotation hash across the four Y-axis rotations.
6. Separately compute an occupancy-only hash to detect recolors/material substitutions.
7. Keep mirror-equivalence **off by default**, especially for redstone and directional machinery.

When rotating data augmentation, transform state properties too: `facing`, `axis`, stairs, rails, doors, trapdoors, beds, repeaters, comparators and modded directional properties.

## Split policy

Split by **canonical source build before augmentation**.

Wrong:

``\`text
train: castle rotated 90°
test: same castle rotated 0°
``\`

Correct:

``\`text
build_id ABC -> train only
all rotations/captions/renders of ABC -> train only
``\`

This prevents severe train/test leakage.


## Scale expectations

There is no verified public corpus found in this audit that simultaneously provides:

- 100k unique human-built structures;
- native dimensions;
- full modern block states;
- strong natural-language annotations;
- images;
- and clearly permissive commercial redistribution/training rights.

Large raw corpora exist, but provenance/licensing is the bottleneck.

A high-quality GabCon dataset can reach very large SFT sizes through leakage-safe augmentation. For example, 10k genuinely unique builds x 4 rotations x 3 text variants = 120k SFT pairs, while still reporting the honest base count as 10k unique structures.

## Next implementation steps

1. Add an importer registry keyed by the machine-readable catalogue in `docs/dataset_sources.json`.
2. Add per-source adapters without changing the canonical structure schema.
3. Add a rights/provenance manifest to every imported record.
4. Add canonical structure hashing and cross-source deduplication.
5. Render all accepted structures through BuildAI's own renderer so image supervision is consistent.
6. Generate rich captions only after retaining original human metadata separately.
7. Build train/validation/test splits at the canonical-build level before augmentation.
8. Never merge restricted/non-commercial data into a redistributable/commercial release by accident.

```


---

## docs/dataset_sources.json

```text
{
  "schema_version": 1,
  "researched_at": "2026-09-28",
  "purpose": "Minecraft build/dataset/source inventory for GabCon BuildAI. Counts from derivatives must not be summed with upstream lineages.",
  "sources": [
    {
      "id": "hack337-minecraft-schematics",
      "name": "Hack337/Minecraft-Schematics",
      "type": "dataset",
      "urls": [
        "https://huggingface.co/datasets/Hack337/Minecraft-Schematics",
        "https://huggingface.co/datasets/Hack337/Minecraft-Schematics/blob/main/README.md"
      ],
      "unique_count_estimate": 669,
      "count_kind": "builds",
      "sft_examples": 1338,
      "text": true,
      "images": false,
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "block_names": true,
      "block_states": "partial/verify",
      "lineage_root": "hack337-minecraft-schematics",
      "notes": "Strongest directly usable text-to-structure seed found. Preserve build-level provenance for deduplication."
    },
    {
      "id": "rom1504-minecraft-schematics-dataset",
      "name": "rom1504/minecraft-schematics-dataset",
      "type": "dataset",
      "urls": [
        "https://github.com/rom1504/minecraft-schematics-dataset",
        "https://gitlab.com/rom1504/minecraft-schematics-dataset"
      ],
      "unique_count_estimate": 8328,
      "count_kind": "records/build lineage",
      "text": true,
      "images": false,
      "voxels": true,
      "raw_schematics": "external/upstream",
      "native_dimensions": false,
      "block_names": "derivable",
      "block_states": true,
      "lineage_root": "rom1504-lineage",
      "notes": "Parent lineage for Farhan and other readers/mirrors. Planet Minecraft-derived metadata."
    },
    {
      "id": "farhanwew-minecraft-schematics-dataset",
      "name": "farhanwew/minecraft-schematics-dataset",
      "type": "dataset-derivative",
      "urls": [
        "https://github.com/farhanwew/minecraft-schematics-dataset"
      ],
      "unique_count_estimate": 8328,
      "count_kind": "same records as rom1504 lineage",
      "text": true,
      "images": true,
      "voxels": true,
      "raw_schematics": "linked/upstream",
      "native_dimensions": false,
      "voxel_shape": [
        32,
        32,
        32
      ],
      "block_names": true,
      "block_states": true,
      "minecraft_mapping_version": "1.16.4",
      "lineage_root": "rom1504-lineage",
      "parent": "rom1504-minecraft-schematics-dataset",
      "notes": "Adds Parquet, voxel_name_data and multiview manifests. Do not count as new independent builds."
    },
    {
      "id": "information-retrieval-4-reader",
      "name": "information-retrieval-4/minecraft-schematics-dataset-reader",
      "type": "tooling-derivative",
      "urls": [
        "https://github.com/information-retrieval-4/minecraft-schematics-dataset-reader"
      ],
      "unique_count_estimate": 0,
      "count_kind": "new unique builds",
      "text": true,
      "images": true,
      "voxels": true,
      "raw_schematics": false,
      "native_dimensions": false,
      "lineage_root": "rom1504-lineage",
      "notes": "Reader/rendering/preprocessing derivative for the same 8,328-record corpus."
    },
    {
      "id": "k1a11220-mirror",
      "name": "k1a11220/minecraft-schematics-dataset",
      "type": "mirror",
      "urls": [
        "https://github.com/k1a11220/minecraft-schematics-dataset"
      ],
      "unique_count_estimate": 0,
      "count_kind": "new unique builds",
      "lineage_root": "rom1504-lineage",
      "notes": "Mirror/fork of rom1504 lineage; not an independent dataset."
    },
    {
      "id": "3d-craft-housecraft",
      "name": "3D-Craft / HouseCraft",
      "type": "dataset",
      "urls": [
        "https://github.com/facebookresearch/voxelcnn",
        "https://craftassist.s3-us-west-2.amazonaws.com/pubr/house_data.tar.gz",
        "https://openaccess.thecvf.com/content_ICCV_2019/html/Chen_Order-Aware_Generative_Modeling_Using_the_3D-Craft_Dataset_ICCV_2019_paper.html"
      ],
      "unique_count_estimate": 2500,
      "count_kind": "human-built houses",
      "text": false,
      "images": "research visuals",
      "voxels": true,
      "raw_schematics": false,
      "native_dimensions": "partially upstream",
      "lineage_root": "3d-craft",
      "notes": "Sequential human build-order data. Excellent 3D/order prior; weak semantic captions."
    },
    {
      "id": "text2mc-dataprocessor",
      "name": "shauncomino/text2mc-dataprocessor",
      "type": "dataset-processing",
      "urls": [
        "https://github.com/shauncomino/text2mc-dataprocessor",
        "https://github.com/shauncomino/text2mc_model"
      ],
      "unique_count_estimate": "~11k viable reported in secondary descriptions; verify exact snapshot",
      "count_kind": "processed player builds",
      "text": true,
      "images": "source-dependent",
      "voxels": true,
      "raw_schematics": "mixed/world source",
      "native_dimensions": "mixed",
      "block_names": true,
      "lineage_root": "text2mc",
      "notes": "Contains Planet Minecraft metadata CSVs, scraping/processing code, world2vec/vec2world and H5 examples."
    },
    {
      "id": "mineanybuild",
      "name": "MineAnyBuild",
      "type": "benchmark",
      "urls": [
        "https://github.com/MineAnyBuild/MineAnyBuild",
        "https://huggingface.co/datasets/SaDil/MineAnyBuild",
        "https://huggingface.co/datasets/SaDil/MineAnyBuild-Raw_data",
        "https://arxiv.org/abs/2505.20148"
      ],
      "unique_count_estimate": 4000,
      "count_kind": "tasks, not necessarily unique builds",
      "text": true,
      "images": true,
      "voxels": "reconstructible",
      "raw_schematics": "partial/architecture data",
      "native_dimensions": true,
      "lineage_root": "mineanybuild",
      "notes": "Best treated as multimodal spatial-planning benchmark/evaluation source. Raw data includes GrabCraft-derived material."
    },
    {
      "id": "minecraft-fable-schem-final",
      "name": "TheAIdude303/Minecraft-Fable-Schem-final",
      "type": "dataset",
      "urls": [
        "https://huggingface.co/datasets/TheAIdude303/Minecraft-Fable-Schem-final"
      ],
      "unique_count_estimate": 6566,
      "count_kind": "native .schem manifest entries observed during audit",
      "text": "mostly filenames",
      "images": false,
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "block_names": true,
      "block_states": true,
      "lineage_root": "fable-unknown",
      "notes": "Technically valuable native/normalized split; provenance should be reconstructed."
    },
    {
      "id": "schematic-diffusion-corpus",
      "name": "KHROTU/schematic-diffusion external corpus",
      "type": "dataset-external",
      "urls": [
        "https://github.com/KHROTU/schematic-diffusion"
      ],
      "unique_count_estimate": "~120k raw files claimed; not verified unique",
      "count_kind": "raw schematic files",
      "text": "filename-derived labels",
      "images": "planned",
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "block_names": true,
      "lineage_root": "schematic-diffusion-external",
      "notes": "Large-scale source. Requires provenance reconstruction and geometric deduplication."
    },
    {
      "id": "litematica-gpt",
      "name": "lukeclaw/litematica-gpt",
      "type": "dataset-and-pipeline",
      "urls": [
        "https://github.com/lukeclaw/litematica-gpt",
        "https://github.com/lukeclaw/litematica-gpt/blob/main/MODELS.md"
      ],
      "unique_count_estimate": 3165,
      "count_kind": "documented DSL blueprints",
      "text": true,
      "images": false,
      "voxels": "DSL -> blocks",
      "raw_schematics": "raw corpus local-only",
      "native_dimensions": true,
      "lineage_root": "litematica-gpt",
      "notes": "Highly relevant prompt -> planner -> compiler/DSL representation. Full scraped raw corpus is not committed."
    },
    {
      "id": "constraint-learnability-regime-map",
      "name": "crabsatellite/constraint-learnability-regime-map",
      "type": "research-derivative",
      "urls": [
        "https://github.com/crabsatellite/constraint-learnability-regime-map"
      ],
      "unique_count_estimate": 0,
      "count_kind": "new unique builds",
      "reported_filtered_builds": 10310,
      "text": "structural conditions",
      "images": false,
      "voxels": true,
      "raw_schematics": false,
      "native_dimensions": false,
      "lineage_root": "multi-source-derivative",
      "notes": "Combines Text2MC, 3D-Craft and rom1504. Excellent preprocessing/feature/control reference; not 10,310 new independent builds."
    },
    {
      "id": "voxel-vae",
      "name": "ms0k/voxel-vae",
      "type": "research-derivative",
      "urls": [
        "https://github.com/ms0k/voxel-vae"
      ],
      "unique_count_estimate": 0,
      "count_kind": "new unique builds",
      "lineage_root": "3d-craft",
      "notes": "Voxel generation/modeling reference; underlying source lineage should not be double-counted."
    },
    {
      "id": "scaffold-diffusion",
      "name": "jsjung00/scaffold-diffusion",
      "type": "research-derivative",
      "urls": [
        "https://github.com/jsjung00/scaffold-diffusion"
      ],
      "unique_count_estimate": 0,
      "count_kind": "new unique builds",
      "lineage_root": "3d-craft",
      "notes": "Generative research derivative; not an independent build corpus."
    },
    {
      "id": "minegen",
      "name": "Viibrant/MineGen",
      "type": "research-pipeline",
      "urls": [
        "https://github.com/Viibrant/MineGen"
      ],
      "unique_count_estimate": "not published clearly",
      "count_kind": "dataset pipeline",
      "text": "metadata scraping planned",
      "images": false,
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": "source-dependent",
      "notes": "Contains scraping/dataset-building and transformer generation pipeline, but no clearly documented standalone public corpus."
    },
    {
      "id": "minecraft-schematic-generator",
      "name": "mmmfrieddough/minecraft-schematic-generator",
      "type": "research-pipeline",
      "urls": [
        "https://github.com/mmmfrieddough/minecraft-schematic-generator",
        "https://huggingface.co/mmmfrieddough/minecraft-schematic-generator"
      ],
      "unique_count_estimate": "not published clearly",
      "count_kind": "world samples",
      "text": false,
      "images": false,
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": "source-dependent",
      "notes": "Useful world sampling, dataset compilation, training and inference reference."
    },
    {
      "id": "computational-redstone",
      "name": "Rektoooooo/computational-redstone",
      "type": "collection",
      "urls": [
        "https://github.com/Rektoooooo/computational-redstone"
      ],
      "unique_count_estimate": 195,
      "count_kind": "functional components from 19 worlds",
      "text": true,
      "images": "some",
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "block_names": true,
      "block_states": true,
      "lineage_root": "computational-redstone",
      "notes": "High-value functional redstone components and manifests; source-world provenance helps deduplication."
    },
    {
      "id": "3d-artefacts-nca",
      "name": "real-itu/3d-artefacts-nca",
      "type": "research-collection",
      "urls": [
        "https://github.com/real-itu/3d-artefacts-nca",
        "https://arxiv.org/abs/2103.08737"
      ],
      "unique_count_estimate": "small",
      "count_kind": "NBT target structures",
      "text": "names/functions",
      "images": true,
      "voxels": true,
      "raw_schematics": "NBT",
      "native_dimensions": true,
      "lineage_root": "3d-artefacts-nca",
      "notes": "Small high-quality corpus of structural/functional targets for Neural Cellular Automata."
    },
    {
      "id": "gdmc2024",
      "name": "Niels-NTG/GDMC2024",
      "type": "research-collection",
      "urls": [
        "https://github.com/Niels-NTG/GDMC2024"
      ],
      "unique_count_estimate": "small",
      "count_kind": "hand-authored pre-built NBT structures",
      "text": "semantic class/code",
      "images": true,
      "voxels": true,
      "raw_schematics": "NBT",
      "native_dimensions": true,
      "minecraft_version": "1.20.2",
      "lineage_root": "gdmc2024",
      "notes": "Useful modular structures with behavior/composition logic."
    },
    {
      "id": "gdmc2023",
      "name": "Niels-NTG/GDMC2023",
      "type": "research-collection",
      "urls": [
        "https://github.com/Niels-NTG/GDMC2023"
      ],
      "unique_count_estimate": "small",
      "count_kind": "hand-authored pre-built NBT structures",
      "text": "semantic class/code",
      "images": true,
      "voxels": true,
      "raw_schematics": "NBT",
      "native_dimensions": true,
      "minecraft_version": "1.19.2",
      "lineage_root": "gdmc2023",
      "notes": "Useful modular settlement structures and composition logic."
    },
    {
      "id": "silvicky-litematics",
      "name": "silvicky/litematics",
      "type": "collection",
      "urls": [
        "https://github.com/silvicky/litematics"
      ],
      "unique_count_estimate": "not audited",
      "count_kind": "litematic files",
      "text": "filenames/folders",
      "images": false,
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "lineage_root": "silvicky-litematics",
      "notes": "Public binary collection with minimal provenance/license documentation."
    },
    {
      "id": "piscescup-mc-java-schematics",
      "name": "Piscescup/MC-Java-Schematics",
      "type": "collection",
      "urls": [
        "https://github.com/Piscescup/MC-Java-Schematics"
      ],
      "unique_count_estimate": "not audited",
      "count_kind": "schematic files",
      "text": "filenames/folders",
      "images": "unknown",
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "lineage_root": "piscescup-schematics",
      "notes": "Large binary repository with limited documentation; manual review required."
    },
    {
      "id": "world-structures",
      "name": "ERGeorgiev/minecraft-schematics-world-structures",
      "type": "collection",
      "urls": [
        "https://github.com/ERGeorgiev/minecraft-schematics-world-structures"
      ],
      "unique_count_estimate": 1,
      "count_kind": "schem entries observed at audit time",
      "text": true,
      "images": true,
      "voxels": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "lineage_root": "world-structures",
      "notes": "Community-driven 1:1 real-world structures. Strong opt-in collection pattern but currently tiny."
    },
    {
      "id": "minecraftschematic-hf",
      "name": "MinecraftSchematic/Schematics",
      "type": "dataset",
      "urls": [
        "https://huggingface.co/datasets/MinecraftSchematic/Schematics"
      ],
      "unique_count_estimate": 2,
      "count_kind": "ZIP archives observed",
      "text": "filenames",
      "images": false,
      "voxels": "inside archives",
      "raw_schematics": true,
      "native_dimensions": true,
      "lineage_root": "minecraftschematic-hf",
      "notes": "Tiny version-labelled release; not useful for scale."
    },
    {
      "id": "dreamcubed-human",
      "name": "dream-cubed/DreamCubedHuman",
      "type": "dataset",
      "urls": [
        "https://huggingface.co/datasets/dream-cubed/DreamCubedHuman"
      ],
      "unique_count_estimate": "1M-10M samples",
      "count_kind": "32^3 chunks, not whole builds",
      "text": "source/class labels only",
      "images": false,
      "voxels": true,
      "raw_schematics": false,
      "native_dimensions": false,
      "voxel_shape": [
        32,
        32,
        32
      ],
      "lineage_root": "dreamcubed-human",
      "notes": "Six human-authored map sources with explicit non-commercial research permission."
    },
    {
      "id": "dreamcubed-natural",
      "name": "dream-cubed/DreamCubedNatural",
      "type": "dataset",
      "urls": [
        "https://huggingface.co/datasets/dream-cubed/DreamCubedNatural"
      ],
      "unique_count_estimate": "large",
      "count_kind": "natural terrain chunks",
      "text": "biome/class labels",
      "images": false,
      "voxels": true,
      "raw_schematics": false,
      "native_dimensions": false,
      "lineage_root": "dreamcubed-natural",
      "notes": "Environment/terrain prior; keep separate from human-build counts."
    },
    {
      "id": "midas",
      "name": "MinecraftDataset/MiDaS",
      "type": "vision-dataset",
      "urls": [
        "https://github.com/MinecraftDataset/MiDaS",
        "https://osf.io/whgy6/"
      ],
      "unique_count_estimate": 36000,
      "count_kind": "images, not builds",
      "text": "block class labels",
      "images": true,
      "voxels": false,
      "raw_schematics": false,
      "native_dimensions": false,
      "notes": "60 block-level classes. Useful for visual/block recognition, not schematic generation counts."
    },
    {
      "id": "craftassist",
      "name": "facebookresearch/craftassist",
      "type": "research-ecosystem",
      "urls": [
        "https://github.com/facebookresearch/craftassist"
      ],
      "unique_count_estimate": 0,
      "count_kind": "independent build count not assigned here",
      "text": true,
      "images": "mixed",
      "voxels": "mixed",
      "raw_schematics": "mixed",
      "native_dimensions": "mixed",
      "lineage_root": "craftassist",
      "notes": "Important instruction-following and house-data ecosystem; links to 3D-Craft/HouseCraft resources."
    },
    {
      "id": "generative-minecraft",
      "name": "hmhornung/Generative-Minecraft",
      "type": "research-derivative",
      "urls": [
        "https://github.com/hmhornung/Generative-Minecraft"
      ],
      "unique_count_estimate": 0,
      "count_kind": "new unique builds",
      "lineage_root": "text2mc",
      "notes": "Recreating Text2MC VAE results with player build data."
    },
    {
      "id": "minecraft2token",
      "name": "hmhornung/Minecraft2Token",
      "type": "tooling",
      "urls": [
        "https://github.com/hmhornung/Minecraft2Token"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "lineage_root": "text2mc",
      "notes": "Tokenization/vocabulary helper; not a standalone corpus."
    },
    {
      "id": "planet-minecraft",
      "name": "Planet Minecraft",
      "type": "source-website",
      "urls": [
        "https://www.planetminecraft.com/"
      ],
      "unique_count_estimate": "large",
      "count_kind": "public projects",
      "text": true,
      "images": true,
      "raw_schematics": "often downloads/worlds",
      "notes": "Terms prohibit systematic extraction, redistribution and embedding/importing site data without written permission."
    },
    {
      "id": "grabcraft",
      "name": "GrabCraft",
      "type": "source-website",
      "urls": [
        "https://www.grabcraft.com/"
      ],
      "unique_count_estimate": "large",
      "count_kind": "blueprints",
      "text": true,
      "images": true,
      "raw_schematics": false,
      "notes": "Do not bulk scrape or use as unrestricted commercial training corpus."
    },
    {
      "id": "minecraft-schematics-com",
      "name": "Minecraft-Schematics.com",
      "type": "source-website",
      "urls": [
        "https://www.minecraft-schematics.com/"
      ],
      "unique_count_estimate": "large",
      "count_kind": "schematics",
      "text": true,
      "images": true,
      "raw_schematics": true,
      "native_dimensions": true,
      "notes": "Discovery/permission workflow source; author-level rights must be obtained/verified."
    },
    {
      "id": "schematic-ai-studio",
      "name": "gamerover98/Schematic-Ai-Studio",
      "type": "tooling",
      "urls": [
        "https://github.com/gamerover98/Schematic-Ai-Studio"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "notes": "Useful compatibility reference for MCEdit schematic, Sponge v2/v3, Litematica and mcfunction conversion/loss reporting."
    },
    {
      "id": "makeschem",
      "name": "mortie/makeschem",
      "type": "tooling",
      "urls": [
        "https://github.com/mortie/makeschem"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "notes": "Minimal text x/y/z/block -> legacy schematic converter; useful as an interchange reference."
    },
    {
      "id": "minecraft-data",
      "name": "PrismarineJS/minecraft-data",
      "type": "registry-reference",
      "urls": [
        "https://github.com/PrismarineJS/minecraft-data"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "notes": "Versioned block/item/protocol registry and legacy mapping reference."
    },
    {
      "id": "mcmeta",
      "name": "misode/mcmeta",
      "type": "registry-reference",
      "urls": [
        "https://github.com/misode/mcmeta"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "notes": "Blockstate/registry metadata reference across Minecraft versions."
    },
    {
      "id": "litematica",
      "name": "maruohon/litematica",
      "type": "format-reference",
      "urls": [
        "https://github.com/maruohon/litematica"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "notes": "Reference implementation for Litematica format behavior/version compatibility."
    },
    {
      "id": "litemapy",
      "name": "SmylerMC/litemapy",
      "type": "format-reference",
      "urls": [
        "https://github.com/SmylerMC/litemapy"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "notes": "Python Litematica parser/writer reference."
    },
    {
      "id": "worldedit",
      "name": "EngineHub/WorldEdit",
      "type": "format-reference",
      "urls": [
        "https://github.com/EngineHub/WorldEdit"
      ],
      "unique_count_estimate": 0,
      "count_kind": "builds",
      "notes": "Canonical ecosystem reference for modern schematic import/export behavior."
    }
  ]
}

```
