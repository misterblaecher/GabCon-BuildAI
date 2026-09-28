"""Generic public GitHub collection discovery for Minecraft structure files."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from mcbuild.dataset.models import SourceItem

_DEFAULT_EXTENSIONS = (
    ".schem",
    ".schematic",
    ".litematic",
    ".nbt",
    ".zip",
    ".tar.gz",
    ".tgz",
)


class GitHubCollectionSource:
    def __init__(
        self,
        *,
        source_id: str,
        display_name: str,
        repository: str,
        branch: str | None = None,
        lineage_dataset: str | None = None,
        lineage_parent: str | None = None,
        extensions: tuple[str, ...] = _DEFAULT_EXTENSIONS,
    ) -> None:
        self.source_id = source_id
        self.display_name = display_name
        self.repository = repository
        self.branch = branch
        self.lineage_dataset = lineage_dataset or repository
        self.lineage_parent = lineage_parent
        self.extensions = tuple(extension.lower() for extension in extensions)

    def discover(self) -> list[SourceItem]:
        repo = urllib.parse.quote(self.repository, safe="/")
        headers = {
            "User-Agent": "mcbuild-dataset/0.1",
            "Accept": "application/vnd.github+json",
        }
        branch_name = self.branch
        if branch_name is None:
            request = urllib.request.Request(f"https://api.github.com/repos/{repo}", headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - constructed internally
                metadata = json.loads(response.read().decode("utf-8"))
            branch_name = str(metadata.get("default_branch") or "main")
        branch = urllib.parse.quote(branch_name, safe="")
        url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - constructed internally
            raw = json.loads(response.read().decode("utf-8"))
        if raw.get("truncated"):
            raise ValueError(f"GitHub tree for {self.repository} is truncated; use a narrower collection adapter.")

        items: list[SourceItem] = []
        for entry in raw.get("tree", []):
            if entry.get("type") != "blob":
                continue
            source_file = str(entry.get("path", ""))
            lower = source_file.lower()
            if not any(lower.endswith(extension) for extension in self.extensions):
                continue
            quoted_path = urllib.parse.quote(source_file, safe="/")
            items.append(
                SourceItem(
                    source=self.source_id,
                    source_item_id=str(entry.get("sha") or source_file),
                    source_url=(f"https://github.com/{self.repository}/blob/{branch_name}/{quoted_path}"),
                    download_url=(f"https://raw.githubusercontent.com/{self.repository}/{branch_name}/{quoted_path}"),
                    source_file=source_file,
                    title=source_file.rsplit("/", 1)[-1].rsplit(".", 1)[0],
                    expected_size=int(entry["size"]) if entry.get("size") is not None else None,
                    lineage_dataset=self.lineage_dataset,
                    lineage_parent=self.lineage_parent,
                    metadata={
                        "git_blob_sha": entry.get("sha"),
                        "repository": self.repository,
                    },
                )
            )
        return items
