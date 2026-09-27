# Full Valley Assembly

The valley is authored as separate mcbuild blueprint modules and assembled before
the final schematic export. This is safer and easier to revise than editing one huge
blueprint.

Current module layout lives in `composition/valley-layout.json`.

## Build the combined schematic

```powershell
uv run python tools/assemble_blueprints.py composition/valley-layout.json
```

If the registry is not already configured through `MCBUILD_SERVER_REGISTRY`:

```powershell
uv run python tools/assemble_blueprints.py composition/valley-layout.json --registry "A:\MinecraftServer\config\mcbuild\server-block-registry.json"
```

Output:

```text
generated/00-full-valley/
├── final.schem
├── render.png
└── stats.json
```

The disabled modules in the JSON are placeholders. Enable each one after its
blueprint has been generated and its standalone render has been approved.

The complete composition is intentionally kept within the mcbuild 512-block axis
guard. Final offsets can be adjusted after all module sizes are known.

Overlaps are allowed and later modules overwrite earlier blocks. The stats file
records how many coordinates overlapped so accidental collisions are visible.
