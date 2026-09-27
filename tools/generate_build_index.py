#!/usr/bin/env python3
"""Regenerate generated/index.json for the static BuildAI gallery."""

from __future__ import annotations

import argparse
from pathlib import Path

from mcbuild.gallery import generate_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the BuildAI gallery manifest.")
    parser.add_argument("--root", type=Path, default=Path("generated"))
    args = parser.parse_args()

    manifest = generate_index(args.root)
    print(f"Wrote {args.root / 'index.json'} with {len(manifest['builds'])} build(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
