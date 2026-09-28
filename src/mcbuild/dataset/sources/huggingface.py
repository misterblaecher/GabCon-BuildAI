"""Hugging Face Hub dataset-file discovery without duplicating download logic."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any

from mcbuild.dataset.models import SourceItem

_NEXT_LINK = re.compile(r'<([^>]+)>;\s*rel="next"')
_DEFAULT_EXTENSIONS = (
    ".schem",
    ".schematic",
    ".litematic",
    ".nbt",
    ".zip",
    ".tar.gz",
    ".tgz",
)


def _request_json(url: str) -> tuple[Any, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "mcbuild-dataset/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - Hub URL constructed internally
        data = json.loads(response.read().decode("utf-8"))
        link = response.headers.get("Link")
    match = _NEXT_LINK.search(link or "")
    return data, match.group(1) if match else None


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "mcbuild-dataset/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - Hub URL constructed internally
        return json.loads(response.read().decode("utf-8"))


class HuggingFaceSource:
    def __init__(
        self,
        *,
        source_id: str,
        display_name: str,
        dataset_id: str,
        lineage_dataset: str | None = None,
        lineage_parent: str | None = None,
        include_prefixes: tuple[str, ...] = (),
        extensions: tuple[str, ...] = _DEFAULT_EXTENSIONS,
    ) -> None:
        self.source_id = source_id
        self.display_name = display_name
        self.dataset_id = dataset_id
        self.lineage_dataset = lineage_dataset or dataset_id
        self.lineage_parent = lineage_parent
        self.include_prefixes = include_prefixes
        self.extensions = tuple(ext.lower() for ext in extensions)

    def _tree(self) -> list[dict[str, Any]]:
        dataset = urllib.parse.quote(self.dataset_id, safe="/")
        url: str | None = (
            f"https://huggingface.co/api/datasets/{dataset}/tree/main?recursive=true&expand=false&limit=1000"
        )
        entries: list[dict[str, Any]] = []
        while url:
            page, url = _request_json(url)
            if not isinstance(page, list):
                raise ValueError(f"Unexpected Hugging Face tree response for {self.dataset_id}")
            entries.extend(entry for entry in page if isinstance(entry, dict))
        return entries

    def _mapping(self, paths: set[str]) -> dict[str, dict[str, Any]]:
        candidates = ("schematics_mapping.json", "mapping.json", "metadata.json")
        mapping_path = next((candidate for candidate in candidates if candidate in paths), None)
        if mapping_path is None:
            return {}
        dataset = urllib.parse.quote(self.dataset_id, safe="/")
        path = urllib.parse.quote(mapping_path, safe="/")
        raw = _fetch_json(f"https://huggingface.co/datasets/{dataset}/resolve/main/{path}")
        if not isinstance(raw, dict):
            return {}
        out: dict[str, dict[str, Any]] = {}
        for key, value in raw.items():
            if isinstance(value, str):
                out[str(key)] = {"title": value}
            elif isinstance(value, dict):
                out[str(key)] = dict(value)
        return out

    def discover(self) -> list[SourceItem]:
        tree = self._tree()
        paths = {str(entry.get("path", "")) for entry in tree}
        mapping = self._mapping(paths)
        dataset = urllib.parse.quote(self.dataset_id, safe="/")
        items: list[SourceItem] = []
        for entry in tree:
            if entry.get("type") != "file":
                continue
            source_file = str(entry.get("path", ""))
            lower = source_file.lower()
            if self.include_prefixes and not any(source_file.startswith(prefix) for prefix in self.include_prefixes):
                continue
            if not any(lower.endswith(extension) for extension in self.extensions):
                continue

            basename = source_file.rsplit("/", 1)[-1]
            metadata = (
                mapping.get(source_file) or mapping.get(basename) or mapping.get(basename.rsplit(".", 1)[0]) or {}
            )
            title = metadata.get("title") or metadata.get("name")
            description = metadata.get("description") or metadata.get("desc")
            tags_raw = metadata.get("tags") or []
            tags = tuple(str(value) for value in tags_raw) if isinstance(tags_raw, list) else ()
            path = urllib.parse.quote(source_file, safe="/")
            lfs = entry.get("lfs") if isinstance(entry.get("lfs"), dict) else {}
            oid = str(lfs.get("oid", ""))
            expected_sha256 = oid if oid.startswith("sha256:") else None
            items.append(
                SourceItem(
                    source=self.source_id,
                    source_item_id=source_file,
                    source_url=f"https://huggingface.co/datasets/{dataset}/blob/main/{path}",
                    download_url=f"https://huggingface.co/datasets/{dataset}/resolve/main/{path}",
                    source_file=source_file,
                    title=str(title) if title else None,
                    description=str(description) if description else None,
                    tags=tags,
                    expected_size=int(entry["size"]) if entry.get("size") is not None else None,
                    expected_sha256=expected_sha256,
                    lineage_dataset=self.lineage_dataset,
                    lineage_parent=self.lineage_parent,
                    metadata={"hub_dataset": self.dataset_id, "hub_oid": entry.get("oid")},
                )
            )
        priority = {
            ".schem": 0,
            ".litematic": 1,
            ".nbt": 2,
            ".schematic": 3,
            ".zip": 4,
            ".tgz": 5,
        }
        items.sort(
            key=lambda item: (
                priority.get(
                    next(
                        (ext for ext in priority if item.source_file.lower().endswith(ext)),
                        "",
                    ),
                    9,
                ),
                item.source_file,
            )
        )
        return items
