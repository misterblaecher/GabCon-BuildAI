"""End-to-end acquisition -> parse -> normalize -> hash -> manifest pipeline."""

from __future__ import annotations

import gzip
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path, PurePosixPath

from mcbuild.dataset.downloader import download_file, extract_archive, file_sha256
from mcbuild.dataset.formats import container_reader_for, read_structure, reader_for
from mcbuild.dataset.hashing import structure_hashes
from mcbuild.dataset.manifest import ManifestDB
from mcbuild.dataset.models import DownloadResult, SourceItem
from mcbuild.dataset.registry import SourceSpec
from mcbuild.dataset.sources.base import DatasetSource


class DatasetPipeline:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.extracted_dir = data_dir / "extracted"
        self.canonical_dir = data_dir / "canonical"
        self.manifest_dir = data_dir / "manifests"
        self.cache_dir = data_dir / "cache"
        for directory in (self.raw_dir, self.extracted_dir, self.canonical_dir, self.manifest_dir, self.cache_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.manifest = ManifestDB(self.manifest_dir / "downloads.sqlite")

    @staticmethod
    def _safe_relative(source_file: str) -> Path:
        pure = PurePosixPath(source_file)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"Unsafe source path: {source_file!r}")
        return Path(*pure.parts)

    def _raw_path(self, item: SourceItem) -> Path:
        return self.raw_dir / item.source / self._safe_relative(item.source_file)

    def _reuse_existing(self, item: SourceItem, destination: Path) -> DownloadResult | None:
        row = self.manifest.file_by_url(item.download_url)
        if row is None and item.expected_sha256:
            row = self.manifest.file_by_hash(item.expected_sha256.removeprefix("sha256:"))
        if row is None or not row["raw_path"]:
            return None
        existing = Path(row["raw_path"])
        if not existing.is_file():
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        if existing.resolve() != destination.resolve():
            try:
                os.link(existing, destination)
            except OSError:
                shutil.copy2(existing, destination)
        return DownloadResult(
            destination,
            str(row["file_sha256"]),
            int(row["file_size"]),
            resumed=False,
        )

    def _download_one(self, item: SourceItem) -> tuple[SourceItem, DownloadResult]:
        destination = self._raw_path(item)
        reused = self._reuse_existing(item, destination)
        result = reused or download_file(
            item.download_url,
            destination,
            expected_size=item.expected_size,
            expected_sha256=item.expected_sha256,
        )
        self.manifest.mark_downloaded(item, raw_path=result.path, sha256=result.sha256, size=result.size)
        return item, result

    def _write_canonical(self, item: SourceItem, structure, hashes) -> Path:
        digest = hashes.structure_hash.removeprefix("sha256:")
        path = self.canonical_dir / item.source / f"{digest}.json.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = structure.to_dict()
        payload.update(
            {
                "build_id": hashes.structure_hash,
                "structure_hash": hashes.structure_hash,
                "rotation_hash": hashes.rotation_hash,
                "occupancy_hash": hashes.occupancy_hash,
                "source": item.source,
                "source_item_id": item.source_item_id,
                "source_file": item.source_file,
            }
        )
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return path

    def _store_structure(self, item: SourceItem, structure) -> bool:
        try:
            hashes = structure_hashes(structure)
            canonical_path = self._write_canonical(item, structure, hashes)
            self.manifest.mark_parsed(
                item,
                structure=structure,
                hashes=hashes,
                canonical_path=canonical_path,
            )
            return True
        except Exception as exc:
            self.manifest.mark_error(item.source, item.source_item_id, stage="canonicalize", message=str(exc))
            return False

    def _parse_one(self, item: SourceItem, path: Path) -> bool:
        if reader_for(path) is None:
            self.manifest.mark_error(item.source, item.source_item_id, stage="parse", message=f"Unsupported format: {path.name}")
            return False
        try:
            structure = read_structure(path)
        except Exception as exc:
            self.manifest.mark_error(item.source, item.source_item_id, stage="parse", message=str(exc))
            return False
        return self._store_structure(item, structure)

    def _parse_download(
        self,
        item: SourceItem,
        path: Path,
        *,
        record_limit: int | None = None,
    ) -> tuple[int, int, int]:
        container_reader = container_reader_for(path)
        if container_reader is not None:
            state = self.manifest.item_state(item.source, item.source_item_id)
            file_hash = str(state["file_sha256"]) if state is not None and state["file_sha256"] else file_sha256(path)
            file_size = int(state["file_size"]) if state is not None and state["file_size"] else path.stat().st_size
            parsed = failed = discovered = 0
            try:
                records = container_reader.iter_records(path, limit=record_limit)
                for record in records:
                    discovered += 1
                    child = replace(
                        item,
                        source_item_id=record.source_item_id,
                        source_url=record.source_url or item.source_url,
                        source_file=f"{item.source_file}#{record.source_item_id}",
                        title=record.title,
                        description=record.description,
                        tags=record.tags,
                        minecraft_version=record.minecraft_version,
                        expected_size=file_size,
                        expected_sha256=None,
                        container=False,
                        metadata={
                            **item.metadata,
                            **record.metadata,
                            "container_parent": item.source_item_id,
                        },
                    )
                    self.manifest.upsert_item(child)
                    self.manifest.mark_downloaded(
                        child,
                        raw_path=path,
                        sha256=file_hash,
                        size=file_size,
                    )
                    if record.error or record.structure is None:
                        self.manifest.mark_error(
                            child.source,
                            child.source_item_id,
                            stage="parse",
                            message=record.error or "Container record contains no structure.",
                        )
                        failed += 1
                    elif self._store_structure(child, record.structure):
                        parsed += 1
                    else:
                        failed += 1
            except Exception as exc:
                self.manifest.mark_error(item.source, item.source_item_id, stage="parse-container", message=str(exc))
                return parsed, failed + 1, discovered
            if record_limit is None:
                self.manifest.mark_container_processed(item)
            return parsed, failed, discovered

        lower = path.name.lower()
        if lower.endswith((".zip", ".tar.gz", ".tgz", ".tar")):
            extraction_root = self.extracted_dir / item.source / path.stem
            try:
                files = extract_archive(path, extraction_root)
            except Exception as exc:
                self.manifest.mark_error(item.source, item.source_item_id, stage="extract", message=str(exc))
                return 0, 1, 0
            parsed = failed = discovered = 0
            for extracted in files:
                if reader_for(extracted) is None:
                    continue
                discovered += 1
                relative = extracted.relative_to(extraction_root).as_posix()
                child = replace(
                    item,
                    source_item_id=f"{item.source_item_id}!{relative}",
                    source_file=f"{item.source_file}!{relative}",
                    download_url=item.download_url,
                    expected_size=extracted.stat().st_size,
                    expected_sha256=None,
                    container=False,
                    metadata={**item.metadata, "archive_parent": item.source_item_id, "archive_member": relative},
                )
                self.manifest.upsert_item(child)
                self.manifest.mark_downloaded(
                    child,
                    raw_path=extracted,
                    sha256=file_sha256(extracted),
                    size=extracted.stat().st_size,
                )
                if self._parse_one(child, extracted):
                    parsed += 1
                else:
                    failed += 1
            if item.container:
                self.manifest.mark_container_processed(item)
            return parsed, failed, discovered
        return ((1, 0, 0) if self._parse_one(item, path) else (0, 1, 0))

    def run_source(
        self,
        spec: SourceSpec,
        adapter: DatasetSource,
        *,
        workers: int = 8,
        limit: int | None = None,
    ) -> dict[str, int]:
        self.manifest.register_source(
            spec.source_id,
            name=spec.name,
            source_type=spec.source_type,
            lineage_root=spec.lineage_root,
        )
        items = adapter.discover()
        if limit is not None:
            items = items[: max(0, limit)]
        for item in items:
            self.manifest.upsert_item(item)

        pending: list[SourceItem] = []
        cached_downloads: list[tuple[SourceItem, DownloadResult]] = []
        already_parsed = 0
        for item in items:
            state = self.manifest.item_state(item.source, item.source_item_id)
            raw_path = Path(state["raw_path"]) if state is not None and state["raw_path"] else None
            if state is not None and state["status"] in {"parsed", "container"} and raw_path is not None and raw_path.is_file():
                already_parsed += 1
                continue
            if raw_path is not None and raw_path.is_file() and state["file_sha256"]:
                cached_downloads.append(
                    (item, DownloadResult(raw_path, str(state["file_sha256"]), int(state["file_size"] or raw_path.stat().st_size), False))
                )
                continue
            pending.append(item)

        downloaded: list[tuple[SourceItem, DownloadResult]] = list(cached_downloads)
        download_failed = 0
        max_workers = max(1, min(workers, 32))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._download_one, item): item for item in pending}
            for future in as_completed(futures):
                item = futures[future]
                try:
                    downloaded.append(future.result())
                except Exception as exc:
                    download_failed += 1
                    self.manifest.mark_error(item.source, item.source_item_id, stage="download", message=str(exc))

        parsed = failed = discovered_children = 0
        for item, result in downloaded:
            ok, bad, child_count = self._parse_download(
                item,
                result.path,
                record_limit=limit if item.container and result.path.suffix.lower() == ".parquet" else None,
            )
            parsed += ok
            failed += bad
            discovered_children += child_count

        self.manifest.recompute_duplicates()
        self.manifest.write_jsonl(self.manifest_dir / "structures.jsonl")
        logical_parents = sum(1 for item in items if not item.container)
        logical_downloaded = sum(1 for item, _ in downloaded if not item.container) + discovered_children
        return {
            "discovered": logical_parents + discovered_children,
            "downloaded": logical_downloaded,
            "parsed": parsed,
            "already_parsed": already_parsed,
            "failed": failed + download_failed,
        }
