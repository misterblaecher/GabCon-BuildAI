# GabCon Build Prompts

These prompts define the visual direction and individual modules for the GabCon steampunk fantasy valley.

## Concept-image workflow

For every new module image, combine:

1. `00-master-style.txt`
2. exactly one numbered module prompt

Example:

```text
00-master-style.txt
+
02-cliffside-factory.txt
=
02-cliffside-factory-concept.png
```

The images are schematic-oriented references, not final builds.

Recommended reference filenames:

```text
references/
├── 01-central-portal-concept.png
├── 02-cliffside-factory-concept.png
├── 03-waterfront-city-concept.png
├── 04-observatory-concept.png
├── 05-arcane-complex-concept.png
├── 06-railway-viaduct-concept.png
└── 07-mountain-castle-concept.png
```

## Recommended production order

1. central portal — already in blueprint development
2. waterfront city — wraps around the portal
3. railway viaduct
4. observatory
5. cliffside factory
6. arcane complex
7. mountain castle

The large terrain, lake and mountains are intentionally excluded from individual module prompts.

After each concept image is accepted:

```text
prompt + concept image + GabCon server registry
        ↓
mcbuild blueprint
        ↓
standalone render + .schem
        ↓
composition/valley-layout.json
        ↓
generated/00-full-valley/final.schem
```
