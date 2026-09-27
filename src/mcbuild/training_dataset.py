"""Versioned dataset export for image-to-build fine-tuning."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DATASET_VERSION = 1
DEFAULT_PROMPT = (
    "Reconstruct the Minecraft building shown in the reference images. "
    "Return only a complete valid mcbuild DSL program."
)


def _split_for_id(build_id: str) -> str:
    """Stable 80/10/10 split by build id so camera views cannot leak across splits."""
    bucket = int(hashlib.sha256(build_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "test"


def _relative(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _sample_from_build(build_dir: Path, repository_root: Path) -> dict[str, Any] | None:
    stats_path = build_dir / "stats.json"
    views_path = build_dir / "views.json"
    blueprint_path = build_dir / "blueprint.py"
    schem_path = build_dir / "final.schem"

    required = (stats_path, views_path, blueprint_path, schem_path)
    if not all(path.is_file() for path in required):
        return None

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    view_manifest = json.loads(views_path.read_text(encoding="utf-8"))
    if not isinstance(view_manifest, list):
        return None

    images: list[str] = []
    view_labels: list[str] = []
    for item in view_manifest:
        if not isinstance(item, dict):
            continue
        filename = item.get("file")
        if not isinstance(filename, str):
            continue
        image_path = build_dir / filename
        if not image_path.is_file():
            continue
        images.append(_relative(image_path, repository_root))
        view_labels.append(str(item.get("label") or filename))

    if not images:
        return None

    build_id = build_dir.name
    target = blueprint_path.read_text(encoding="utf-8")

    return {
        "version": DATASET_VERSION,
        "id": build_id,
        "split": _split_for_id(build_id),
        "task": "image_to_mcbuild_dsl",
        "images": images,
        "view_labels": view_labels,
        "prompt": DEFAULT_PROMPT,
        "target": target,
        "metadata": {
            "dims": stats.get("dims"),
            "block_count": stats.get("block_count"),
            "top_materials": stats.get("top_materials", []),
            "namespaces": stats.get("namespaces", {}),
            "stats": _relative(stats_path, repository_root),
            "schematic": _relative(schem_path, repository_root),
            "blueprint": _relative(blueprint_path, repository_root),
        },
    }


def export_dataset(
    generated_root: str | Path = "generated",
    output: str | Path = "training/image_build_v1.jsonl",
    *,
    repository_root: str | Path = ".",
) -> dict[str, int]:
    """Write one JSONL sample per complete generated build and return split counts."""
    root = Path(generated_root)
    repo = Path(repository_root).resolve()
    output_path = Path(output)

    samples: list[dict[str, Any]] = []
    if root.is_dir():
        for build_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            sample = _sample_from_build(build_dir.resolve(), repo)
            if sample is not None:
                samples.append(sample)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")

    counts = {"train": 0, "validation": 0, "test": 0, "total": len(samples)}
    for sample in samples:
        counts[sample["split"]] += 1

    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(
            {
                "version": DATASET_VERSION,
                "task": "image_to_mcbuild_dsl",
                "source": Path(generated_root).as_posix(),
                "dataset": output_path.as_posix(),
                "counts": counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Export generated mcbuild artifacts as an image-to-build dataset.")
    parser.add_argument("--generated", default="generated", help="Root containing generated/<build-id>/ directories.")
    parser.add_argument("--out", default="training/image_build_v1.jsonl", help="Output JSONL path.")
    parser.add_argument("--repo-root", default=".", help="Repository root used for relative paths.")
    args = parser.parse_args()

    counts = export_dataset(args.generated, args.out, repository_root=args.repo_root)
    print(
        "Exported "
        f"{counts['total']} sample(s): "
        f"train={counts['train']} validation={counts['validation']} test={counts['test']} "
        f"-> {args.out}"
    )


if __name__ == "__main__":
    main()
