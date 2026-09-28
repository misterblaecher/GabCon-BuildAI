"""Dataset source registry driven by docs/dataset_sources.json."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcbuild.dataset.sources.base import DatasetSource
from mcbuild.dataset.sources.github_collection import GitHubCollectionSource
from mcbuild.dataset.sources.huggingface import HuggingFaceSource

_HF_RE = re.compile(r"https://huggingface\.co/datasets/([^/?#]+/[^/?#]+)")
_GITHUB_RE = re.compile(r"https://github\.com/([^/?#]+/[^/?#]+)")
_STORAGE_ALIASES = {
    "hack337-minecraft-schematics": "hack337",
    "farhanwew-minecraft-schematics-dataset": "farhanwew",
    "minecraft-fable-schem-final": "fable",
    "schematic-diffusion-corpus": "schematic-diffusion",
}


@dataclass(frozen=True, slots=True)
class SourceSpec:
    catalog_id: str
    source_id: str
    name: str
    source_type: str
    urls: tuple[str, ...]
    lineage_root: str | None
    parent: str | None
    raw: dict[str, Any]

    @property
    def supported(self) -> bool:
        return any(_HF_RE.match(url) or _GITHUB_RE.match(url) for url in self.urls)


class SourceRegistry:
    def __init__(self, specs: list[SourceSpec]) -> None:
        self.specs = specs
        self._names: dict[str, SourceSpec] = {}
        for spec in specs:
            aliases = {
                spec.catalog_id.lower(),
                spec.source_id.lower(),
                spec.name.lower(),
                spec.name.split("/", 1)[-1].lower(),
            }
            for alias in aliases:
                self._names.setdefault(alias, spec)

    @classmethod
    def load(cls, catalog_path: Path | None = None) -> SourceRegistry:
        if catalog_path is None:
            catalog_path = Path(__file__).resolve().parents[3] / "docs" / "dataset_sources.json"
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        entries = raw.get(
            "sources",
            raw if isinstance(raw, list) else [],
        )
        specs: list[SourceSpec] = []
        for entry in entries:
            catalog_id = str(entry["id"])
            specs.append(
                SourceSpec(
                    catalog_id=catalog_id,
                    source_id=_STORAGE_ALIASES.get(
                        catalog_id,
                        catalog_id,
                    ),
                    name=str(entry.get("name") or catalog_id),
                    source_type=str(entry.get("type") or "unknown"),
                    urls=tuple(str(url) for url in entry.get("urls", [])),
                    lineage_root=(str(entry.get("lineage_root")) if entry.get("lineage_root") else None),
                    parent=(str(entry.get("parent")) if entry.get("parent") else None),
                    raw=dict(entry),
                )
            )
        return cls(specs)

    def resolve(self, name: str) -> SourceSpec:
        normalized = name.strip().lower()
        spec = self._names.get(normalized)
        if spec is None:
            choices = ", ".join(sorted(spec.source_id for spec in self.specs if spec.supported)[:20])
            raise KeyError(f"Unknown dataset source {name!r}. Known source ids include: {choices}")
        return spec

    def adapter(self, spec: SourceSpec) -> DatasetSource:
        hf_url = next(
            (url for url in spec.urls if _HF_RE.match(url)),
            None,
        )
        if hf_url:
            match = _HF_RE.match(hf_url)
            assert match is not None
            include_prefixes: tuple[str, ...] = ()
            if spec.source_id == "hack337":
                include_prefixes = ("schematics/",)
            return HuggingFaceSource(
                source_id=spec.source_id,
                display_name=spec.name,
                dataset_id=match.group(1),
                lineage_dataset=spec.lineage_root or spec.catalog_id,
                lineage_parent=spec.parent,
                include_prefixes=include_prefixes,
            )

        github_url = next(
            (url for url in spec.urls if _GITHUB_RE.match(url)),
            None,
        )
        if github_url:
            match = _GITHUB_RE.match(github_url)
            assert match is not None
            return GitHubCollectionSource(
                source_id=spec.source_id,
                display_name=spec.name,
                repository=match.group(1).removesuffix(".git"),
                lineage_dataset=spec.lineage_root or spec.catalog_id,
                lineage_parent=spec.parent,
            )
        raise ValueError(f"No automated adapter is available for {spec.catalog_id}")
