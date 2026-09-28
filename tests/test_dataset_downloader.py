import io
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import pytest

from mcbuild.dataset.downloader import download_file, extract_archive


class _Response(io.BytesIO):
    def __init__(
        self,
        data: bytes,
        *,
        status: int,
        headers: dict[str, str],
    ):
        super().__init__(data)
        self.status = status
        self.headers = headers

    def getcode(self):
        return self.status


def test_download_resumes_part_file(monkeypatch, tmp_path: Path):
    destination = tmp_path / "build.schem"
    part = tmp_path / "build.schem.part"
    part.write_bytes(b"abc")

    def fake_urlopen(request, timeout=0):
        assert request.headers["Range"] == "bytes=3-"
        return _Response(
            b"def",
            status=206,
            headers={
                "Content-Range": "bytes 3-5/6",
                "Content-Length": "3",
            },
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = download_file(
        "https://example.invalid/build.schem",
        destination,
        expected_size=6,
        retries=0,
    )
    assert result.resumed is True
    assert destination.read_bytes() == b"abcdef"
    assert not part.exists()


def test_safe_zip_extraction_rejects_path_traversal(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.schem", b"bad")
    with pytest.raises(ValueError):
        extract_archive(archive, tmp_path / "out")


def test_tar_extraction_ignores_links(tmp_path: Path):
    archive = tmp_path / "ok.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        payload = b"hello"
        info = tarfile.TarInfo("inside/build.schem")
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))
        link = tarfile.TarInfo("inside/link.schem")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tf.addfile(link)
    files = extract_archive(archive, tmp_path / "out")
    assert [
        path.relative_to(tmp_path / "out").as_posix()
        for path in files
    ] == ["inside/build.schem"]
