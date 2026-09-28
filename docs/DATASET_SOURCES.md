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

```text
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
```

Cross-lineage duplicates are also possible because Planet Minecraft-origin structures can appear in multiple scraped/processed corpora.

## Recommended canonical GabCon record

Never make 32^3 the master representation. Keep original geometry and generate normalized views as derivatives.

```json
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
```

Derived artifacts may then include:

```text
canonical sparse structure
├── GabCon Blueprint DSL
├── dense voxel original-size
├── optional 32^3 / 64^3 crops for specific models
├── Sponge v3 .schem
├── 8-12 standardized renders
└── caption/prompt variants
```

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

```text
train: castle rotated 90°
test: same castle rotated 0°
```

Correct:

```text
build_id ABC -> train only
all rotations/captions/renders of ABC -> train only
```

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
