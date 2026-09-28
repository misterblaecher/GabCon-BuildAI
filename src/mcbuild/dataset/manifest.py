"""SQLite-backed resumable sourcing manifest."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcbuild.dataset.models import CanonicalStructure, SourceItem, StructureHashes


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ManifestDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    source_type TEXT,
                    lineage_root TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS items (
                    source TEXT NOT NULL,
                    source_item_id TEXT NOT NULL,
                    source_url TEXT,
                    download_url TEXT,
                    source_file TEXT,
                    title TEXT,
                    description TEXT,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    images_json TEXT NOT NULL DEFAULT '[]',
                    minecraft_version TEXT,
                    lineage_dataset TEXT,
                    lineage_parent TEXT,
                    expected_size INTEGER,
                    expected_sha256 TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    is_container INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'discovered',
                    raw_path TEXT,
                    file_sha256 TEXT,
                    file_size INTEGER,
                    error TEXT,
                    discovered_at TEXT NOT NULL,
                    downloaded_at TEXT,
                    parsed_at TEXT,
                    PRIMARY KEY (source, source_item_id)
                );
                CREATE INDEX IF NOT EXISTS idx_items_status ON items(source, status);
                CREATE INDEX IF NOT EXISTS idx_items_download_url ON items(download_url);
                CREATE INDEX IF NOT EXISTS idx_items_file_hash ON items(file_sha256);
                CREATE TABLE IF NOT EXISTS structures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    source_item_id TEXT NOT NULL,
                    build_id TEXT NOT NULL,
                    structure_hash TEXT NOT NULL,
                    rotation_hash TEXT NOT NULL,
                    occupancy_hash TEXT NOT NULL,
                    canonical_path TEXT NOT NULL,
                    dimensions_json TEXT NOT NULL,
                    block_count INTEGER NOT NULL,
                    volume INTEGER NOT NULL,
                    palette_size INTEGER NOT NULL,
                    duplicate_of TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    UNIQUE(source, source_item_id)
                );
                CREATE INDEX IF NOT EXISTS idx_structures_exact ON structures(structure_hash);
                CREATE INDEX IF NOT EXISTS idx_structures_rotation ON structures(rotation_hash);
                CREATE INDEX IF NOT EXISTS idx_structures_occupancy ON structures(occupancy_hash);
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    source_item_id TEXT,
                    stage TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(items)")}
            if "is_container" not in columns:
                db.execute("ALTER TABLE items ADD COLUMN is_container INTEGER NOT NULL DEFAULT 0")

    def register_source(self, source_id: str, *, name: str, source_type: str, lineage_root: str | None) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO sources(id, name, source_type, lineage_root, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, source_type=excluded.source_type,
                    lineage_root=excluded.lineage_root, updated_at=excluded.updated_at""",
                (source_id, name, source_type, lineage_root, _now()),
            )

    def upsert_item(self, item: SourceItem) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO items(
                    source, source_item_id, source_url, download_url, source_file, title, description,
                    tags_json, images_json, minecraft_version, lineage_dataset, lineage_parent,
                    expected_size, expected_sha256, metadata_json, is_container, discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, source_item_id) DO UPDATE SET
                    source_url=excluded.source_url, download_url=excluded.download_url,
                    source_file=excluded.source_file, title=COALESCE(excluded.title, items.title),
                    description=COALESCE(excluded.description, items.description),
                    tags_json=excluded.tags_json, images_json=excluded.images_json,
                    minecraft_version=COALESCE(excluded.minecraft_version, items.minecraft_version),
                    lineage_dataset=excluded.lineage_dataset, lineage_parent=excluded.lineage_parent,
                    expected_size=COALESCE(excluded.expected_size, items.expected_size),
                    expected_sha256=COALESCE(excluded.expected_sha256, items.expected_sha256),
                    metadata_json=excluded.metadata_json, is_container=excluded.is_container""",
                (
                    item.source,
                    item.source_item_id,
                    item.source_url,
                    item.download_url,
                    item.source_file,
                    item.title,
                    item.description,
                    json.dumps(list(item.tags), ensure_ascii=False),
                    json.dumps(list(item.images), ensure_ascii=False),
                    item.minecraft_version,
                    item.lineage_dataset,
                    item.lineage_parent,
                    item.expected_size,
                    item.expected_sha256,
                    json.dumps(item.metadata, ensure_ascii=False, sort_keys=True),
                    int(item.container),
                    _now(),
                ),
            )

    def item_state(self, source: str, source_item_id: str) -> sqlite3.Row | None:
        with self._connect() as db:
            return db.execute(
                "SELECT * FROM items WHERE source=? AND source_item_id=?", (source, source_item_id)
            ).fetchone()

    def file_by_url(self, url: str) -> sqlite3.Row | None:
        with self._connect() as db:
            return db.execute(
                "SELECT * FROM items WHERE download_url=? AND status IN ('downloaded','parsed','container') ORDER BY downloaded_at LIMIT 1",
                (url,),
            ).fetchone()

    def file_by_hash(self, sha256: str) -> sqlite3.Row | None:
        with self._connect() as db:
            return db.execute(
                "SELECT * FROM items WHERE file_sha256=? AND status IN ('downloaded','parsed','container') ORDER BY downloaded_at LIMIT 1",
                (sha256,),
            ).fetchone()

    def mark_downloaded(self, item: SourceItem, *, raw_path: Path, sha256: str, size: int) -> None:
        with self._connect() as db:
            db.execute(
                """UPDATE items SET status='downloaded', raw_path=?, file_sha256=?, file_size=?,
                    downloaded_at=?, error=NULL WHERE source=? AND source_item_id=?""",
                (str(raw_path), sha256, size, _now(), item.source, item.source_item_id),
            )

    def mark_container_processed(self, item: SourceItem) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE items SET status='container', parsed_at=?, error=NULL WHERE source=? AND source_item_id=?",
                (_now(), item.source, item.source_item_id),
            )

    def duplicate_for_rotation(self, rotation_hash: str, *, exclude_source: str, exclude_item: str) -> sqlite3.Row | None:
        with self._connect() as db:
            return db.execute(
                """SELECT * FROM structures WHERE rotation_hash=? AND NOT (source=? AND source_item_id=?)
                ORDER BY id LIMIT 1""",
                (rotation_hash, exclude_source, exclude_item),
            ).fetchone()

    def mark_parsed(
        self,
        item: SourceItem,
        *,
        structure: CanonicalStructure,
        hashes: StructureHashes,
        canonical_path: Path,
    ) -> None:
        duplicate = self.duplicate_for_rotation(
            hashes.rotation_hash, exclude_source=item.source, exclude_item=item.source_item_id
        )
        duplicate_of = duplicate["build_id"] if duplicate is not None else None
        with self._connect() as db:
            db.execute(
                """INSERT INTO structures(
                    source, source_item_id, build_id, structure_hash, rotation_hash, occupancy_hash,
                    canonical_path, dimensions_json, block_count, volume, palette_size, duplicate_of,
                    metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, source_item_id) DO UPDATE SET
                    build_id=excluded.build_id, structure_hash=excluded.structure_hash,
                    rotation_hash=excluded.rotation_hash, occupancy_hash=excluded.occupancy_hash,
                    canonical_path=excluded.canonical_path, dimensions_json=excluded.dimensions_json,
                    block_count=excluded.block_count, volume=excluded.volume,
                    palette_size=excluded.palette_size, duplicate_of=excluded.duplicate_of,
                    metadata_json=excluded.metadata_json""",
                (
                    item.source,
                    item.source_item_id,
                    hashes.structure_hash,
                    hashes.structure_hash,
                    hashes.rotation_hash,
                    hashes.occupancy_hash,
                    str(canonical_path),
                    json.dumps(list(structure.dimensions)),
                    structure.block_count,
                    structure.volume,
                    structure.palette_size,
                    duplicate_of,
                    json.dumps(structure.metadata, ensure_ascii=False, sort_keys=True),
                    _now(),
                ),
            )
            db.execute(
                "UPDATE items SET status='parsed', parsed_at=?, error=NULL WHERE source=? AND source_item_id=?",
                (_now(), item.source, item.source_item_id),
            )

    def mark_error(self, source: str, source_item_id: str, *, stage: str, message: str) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE items SET status='failed', error=? WHERE source=? AND source_item_id=?",
                (f"{stage}: {message}", source, source_item_id),
            )
            db.execute(
                "INSERT INTO errors(source, source_item_id, stage, message, created_at) VALUES (?, ?, ?, ?, ?)",
                (source, source_item_id, stage, message[:4000], _now()),
            )

    def status_rows(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT i.source,
                    COUNT(*) AS discovered,
                    SUM(CASE WHEN i.downloaded_at IS NOT NULL THEN 1 ELSE 0 END) AS downloaded,
                    SUM(CASE WHEN i.status='parsed' THEN 1 ELSE 0 END) AS parsed,
                    SUM(CASE WHEN i.status='failed' THEN 1 ELSE 0 END) AS failed,
                    COUNT(s.id) - SUM(CASE WHEN s.duplicate_of IS NOT NULL THEN 1 ELSE 0 END) AS unique_count
                FROM items i LEFT JOIN structures s
                    ON s.source=i.source AND s.source_item_id=i.source_item_id
                WHERE i.is_container=0
                GROUP BY i.source ORDER BY i.source"""
            ).fetchall()
        return [dict(row) for row in rows]

    def recompute_duplicates(self) -> int:
        updates = 0
        with self._connect() as db:
            rows = db.execute("SELECT id, build_id, rotation_hash FROM structures ORDER BY id").fetchall()
            first_by_rotation: dict[str, str] = {}
            for row in rows:
                duplicate_of = first_by_rotation.get(row["rotation_hash"])
                if duplicate_of is None:
                    first_by_rotation[row["rotation_hash"]] = row["build_id"]
                db.execute("UPDATE structures SET duplicate_of=? WHERE id=?", (duplicate_of, row["id"]))
                if duplicate_of is not None:
                    updates += 1
        return updates

    def iter_manifest(self):
        with self._connect() as db:
            rows = db.execute(
                """SELECT i.*, s.build_id, s.structure_hash, s.rotation_hash, s.occupancy_hash,
                    s.canonical_path, s.dimensions_json, s.block_count, s.volume, s.palette_size, s.duplicate_of
                FROM items i JOIN structures s ON s.source=i.source AND s.source_item_id=i.source_item_id
                ORDER BY i.source, i.source_item_id"""
            ).fetchall()
        for row in rows:
            yield dict(row)

    def write_jsonl(self, path: Path) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open("w", encoding="utf-8") as handle:
            for row in self.iter_manifest():
                record = {
                    "build_id": row["build_id"],
                    "structure_hash": row["structure_hash"],
                    "rotation_hash": row["rotation_hash"],
                    "occupancy_hash": row["occupancy_hash"],
                    "source": row["source"],
                    "source_item_id": row["source_item_id"],
                    "source_url": row["source_url"],
                    "source_file": row["source_file"],
                    "title": row["title"],
                    "description": row["description"],
                    "tags": json.loads(row["tags_json"]),
                    "minecraft_version": row["minecraft_version"],
                    "dimensions": json.loads(row["dimensions_json"]),
                    "block_count": row["block_count"],
                    "volume": row["volume"],
                    "palette_size": row["palette_size"],
                    "formats": {"original": row["raw_path"], "canonical": row["canonical_path"]},
                    "images": json.loads(row["images_json"]),
                    "lineage": {"dataset": row["lineage_dataset"], "parent": row["lineage_parent"]},
                    "duplicate_of": row["duplicate_of"],
                }
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                count += 1
        return count
