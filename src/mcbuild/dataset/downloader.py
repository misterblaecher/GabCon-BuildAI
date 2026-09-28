"""Resumable downloads and safe archive extraction."""

from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from mcbuild.dataset.models import DownloadResult


class DownloadError(RuntimeError):
    pass


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _target_size(response, offset: int, expected_size: int | None) -> int | None:
    if expected_size is not None:
        return expected_size
    content_range = response.headers.get("Content-Range")
    if content_range and "/" in content_range:
        total = content_range.rsplit("/", 1)[1]
        if total.isdigit():
            return int(total)
    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit():
        return offset + int(content_length)
    return None


def download_file(
    url: str,
    destination: Path,
    *,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    retries: int = 4,
    timeout: float = 30.0,
    user_agent: str = "mcbuild-dataset/0.1",
) -> DownloadResult:
    """Download to a `.part` file, resume with HTTP Range, then atomically rename."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")

    if destination.is_file():
        size = destination.stat().st_size
        digest = file_sha256(destination)
        invalid_size = expected_size is not None and size != expected_size
        invalid_hash = expected_sha256 is not None and digest.lower() != expected_sha256.removeprefix("sha256:").lower()
        if invalid_size or invalid_hash:
            destination.unlink()
        else:
            return DownloadResult(destination, digest, size, resumed=False)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        offset = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": user_agent, "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                status = getattr(response, "status", response.getcode())
                resumed = bool(offset and status == 206)
                if offset and status != 206:
                    offset = 0
                    resumed = False
                    part.unlink(missing_ok=True)
                mode = "ab" if resumed else "wb"
                total_size = _target_size(response, offset, expected_size)
                with part.open(mode) as handle:
                    shutil.copyfileobj(response, handle, length=1024 * 1024)
                actual_size = part.stat().st_size
                if total_size is not None and actual_size != total_size:
                    raise DownloadError(f"Size mismatch for {url}: expected {total_size}, got {actual_size}")
                digest = file_sha256(part)
                if expected_sha256 is not None:
                    wanted = expected_sha256.removeprefix("sha256:").lower()
                    if digest.lower() != wanted:
                        raise DownloadError(f"SHA-256 mismatch for {url}: expected {wanted}, got {digest}")
                os.replace(part, destination)
                return DownloadResult(
                    destination,
                    digest,
                    actual_size,
                    resumed=resumed,
                )
        except (
            OSError,
            urllib.error.URLError,
            urllib.error.HTTPError,
            DownloadError,
        ) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(2**attempt, 16))
    raise DownloadError(f"Failed to download {url}: {last_error}") from last_error


def _safe_output(root: Path, name: str) -> Path:
    root = root.resolve()
    target = (root / name).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Archive path escapes extraction root: {name!r}")
    return target


def extract_archive(path: Path, destination: Path) -> list[Path]:
    """Safely extract zip/tar archives without following archive-provided links."""
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    lower = path.name.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                target = _safe_output(destination, info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
                extracted.append(target)
        return extracted

    if lower.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                target = _safe_output(destination, member.name)
                source = archive.extractfile(member)
                if source is None:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)
                extracted.append(target)
        return extracted

    raise ValueError(f"Unsupported archive type: {path.name}")
