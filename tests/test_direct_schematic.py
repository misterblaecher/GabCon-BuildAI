"""Direct command-line schematic creation, independent of GabCon Studio."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import nbtlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "create_schematic.py"
BLUEPRINT_SCRIPT = ROOT / "tools" / "build_blueprint.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )


def test_direct_from_chatgpt_blueprint_without_api(tmp_path: Path) -> None:
    source = tmp_path / "house.py"
    source.write_text(
        'floor(0, 0, 4, 4, 0, "oak_planks")\nwalls(0, 0, 4, 4, 1, 3, "stone_bricks")\nclear(2, 1, 0, 2, 2, 0)\n',
        encoding="utf-8",
    )
    output = tmp_path / "direct"
    result = _run("--blueprint", str(source), "--out", str(output), "--preview", "none")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "WorldEdit schematic ready" in result.stdout
    assert not (output / "render.png").exists()
    assert (output / "blueprint.py").read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    root = nbtlib.load(str(output / "final.schem"))
    assert int(root["Schematic"]["Version"]) == 3
    stats = json.loads((output / "stats.json").read_text(encoding="utf-8"))
    assert stats["block_count"] > 0
    assert stats["preview"] == "none"

    repeat = _run("--blueprint", str(source), "--out", str(output), "--preview", "none")
    assert repeat.returncode == 1
    assert "--force" in repeat.stderr


def test_direct_schematic_limits_sparse_oversized_volume(tmp_path: Path) -> None:
    source = tmp_path / "oversized.py"
    source.write_text(
        'set_block(0,0,0,"stone")\nset_block(511,511,511,"stone")\n',
        encoding="utf-8",
    )
    result = _run("--blueprint", str(source), "--out", str(tmp_path / "large"), "--preview", "none")
    assert result.returncode == 1
    assert "exceeds safe schematic export limit" in result.stderr
    assert not (tmp_path / "large" / "final.schem").exists()


def test_direct_rejects_bad_inputs_before_api(tmp_path: Path) -> None:
    empty = _run("--prompt", " ", "--out", str(tmp_path / "empty"))
    assert empty.returncode == 1
    assert "non-empty" in empty.stderr
    invalid = _run("--prompt", "castle", "--max-iters", "0", "--out", str(tmp_path / "bad"))
    assert invalid.returncode == 1
    assert "--max-iters" in invalid.stderr
    missing = _run("--blueprint", str(tmp_path / "missing.py"), "--out", str(tmp_path / "missing"))
    assert missing.returncode == 1
    assert "not found" in missing.stderr.lower()


def test_existing_script_supports_fast_preview_without_studio(tmp_path: Path) -> None:
    source = tmp_path / "tiny.py"
    source.write_text('fill(0,0,0,2,1,2,"stone")\n', encoding="utf-8")
    out = tmp_path / "fast"
    result = subprocess.run(
        [sys.executable, str(BLUEPRINT_SCRIPT), str(source), "--out", str(out), "--preview", "fast"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert (out / "render.png").is_file()
    assert (out / "final.schem").is_file()
    stats = json.loads((out / "stats.json").read_text(encoding="utf-8"))
    assert stats["views"] == ["yaw 0deg"]
