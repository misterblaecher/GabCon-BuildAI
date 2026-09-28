"""Source adapter interface."""

from __future__ import annotations

from typing import Protocol

from mcbuild.dataset.models import SourceItem


class DatasetSource(Protocol):
    source_id: str
    display_name: str

    def discover(self) -> list[SourceItem]: ...
