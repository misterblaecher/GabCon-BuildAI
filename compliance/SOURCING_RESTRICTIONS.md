# Sourcing restrictions moved off main

These notes were removed from `main` to keep the development branch focused on technical ingestion/sourcing.
They are preserved here verbatim or semantically equivalent for reference.

## Canonical-record compliance fields previously documented

```json
{
  "rights_grade": "B",
  "dataset_license": "MIT",
  "build_license": null
}
```

## Scale / release constraints previously documented

- and clearly permissive commercial redistribution/training rights.
- Large raw corpora exist, but provenance/licensing is the bottleneck.
- Add a rights/provenance manifest to every imported record.
- Never merge restricted/non-commercial data into a redistributable/commercial release by accident.

## Source-specific restriction notes previously kept in the machine-readable catalog

- silvicky/litematics: Public binary collection with minimal provenance/license documentation.
- Dream-Cubed Human: Six human-authored map sources with explicit non-commercial research permission.
- Planet Minecraft: Terms prohibit systematic extraction, redistribution and embedding/importing site data without written permission.
- GrabCraft: Do not bulk scrape or use as unrestricted commercial training corpus.
- Minecraft-Schematics.com: Discovery/permission workflow source; author-level rights must be obtained/verified.

## README wording previously used

- source-site restrictions
- rights filtering
- licensing/usage notes
