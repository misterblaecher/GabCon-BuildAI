"""Regression tests for GabCon Studio's user-configurable build limit."""
from __future__ import annotations

import runpy
from pathlib import Path

_CONFIG = runpy.run_path(str(Path(__file__).resolve().parents[1] / "gabcon-studio" / "studio_config.py"))
studio_block_limit = _CONFIG["studio_block_limit"]


def test_studio_default_limit(monkeypatch):
    monkeypatch.delenv("GABCON_STUDIO_MAX_BLOCKS", raising=False)
    assert studio_block_limit() == 1_000_000


def test_studio_custom_limit(monkeypatch):
    monkeypatch.setenv("GABCON_STUDIO_MAX_BLOCKS", "2_500_000")
    assert studio_block_limit() == 2_500_000


def test_studio_limit_never_exceeds_engine(monkeypatch):
    monkeypatch.setenv("GABCON_STUDIO_MAX_BLOCKS", "99999999")
    assert studio_block_limit() == 4_000_000


def test_studio_invalid_limit_uses_default(monkeypatch):
    monkeypatch.setenv("GABCON_STUDIO_MAX_BLOCKS", "invalid")
    assert studio_block_limit() == 1_000_000


def test_studio_non_positive_limit_is_safe(monkeypatch):
    monkeypatch.setenv("GABCON_STUDIO_MAX_BLOCKS", "-1")
    assert studio_block_limit() == 1
