"""Server-registry profile loading for Minecraft/NeoForge builds."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGISTRY_ENV = "MCBUILD_SERVER_REGISTRY"


class ProfileError(ValueError):
    """Raised when an exported server registry is malformed or inconsistent."""


@dataclass(frozen=True)
class ServerProfile:
    path: Path
    format_version: int
    minecraft_version: str
    data_version: int
    generated_at: str | None
    namespaces: dict[str, int]
    blocks: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, path: str | Path) -> ServerProfile:
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise ProfileError(f"Server registry not found: {source}")

        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileError(f"Could not read server registry {source}: {exc}") from exc

        if raw.get("format_version") != 1:
            raise ProfileError(
                f"Unsupported server registry format_version={raw.get('format_version')!r}; expected 1."
            )

        blocks = raw.get("blocks")
        if not isinstance(blocks, dict) or not blocks:
            raise ProfileError("Server registry must contain a non-empty 'blocks' object.")

        block_count = raw.get("block_count")
        if block_count != len(blocks):
            raise ProfileError(
                f"Server registry block_count={block_count!r} but contains {len(blocks)} block entries."
            )

        computed_state_count = 0
        namespace_counts: dict[str, int] = {}
        for block_id, entry in blocks.items():
            if not isinstance(block_id, str) or ":" not in block_id:
                raise ProfileError(f"Invalid block ID in server registry: {block_id!r}")
            if not isinstance(entry, dict):
                raise ProfileError(f"Registry entry for {block_id} must be an object.")

            namespace, path_part = block_id.split(":", 1)
            if entry.get("namespace") != namespace or entry.get("path") != path_part:
                raise ProfileError(f"Registry entry metadata does not match ID {block_id}.")

            states = entry.get("states")
            properties = entry.get("properties")
            if not isinstance(states, list) or not states:
                raise ProfileError(f"Registry entry {block_id} has no valid states.")
            if not isinstance(properties, dict):
                raise ProfileError(f"Registry entry {block_id} has invalid properties metadata.")
            if entry.get("state_count") != len(states):
                raise ProfileError(f"Registry entry {block_id} has an inconsistent state_count.")
            if entry.get("default_state") not in states:
                raise ProfileError(f"Registry entry {block_id} default_state is not in its valid states.")

            computed_state_count += len(states)
            namespace_counts[namespace] = namespace_counts.get(namespace, 0) + 1

        if raw.get("state_count") != computed_state_count:
            raise ProfileError(
                f"Server registry state_count={raw.get('state_count')!r} but contains "
                f"{computed_state_count} states."
            )

        namespaces = raw.get("namespaces")
        if namespaces != namespace_counts:
            raise ProfileError(
                f"Server registry namespace counts do not match block entries: "
                f"metadata={namespaces!r}, computed={namespace_counts!r}."
            )

        minecraft_version = raw.get("minecraft_version")
        data_version = raw.get("data_version")
        if not isinstance(minecraft_version, str) or not minecraft_version:
            raise ProfileError("Server registry is missing minecraft_version.")
        if not isinstance(data_version, int):
            raise ProfileError("Server registry is missing an integer data_version.")

        return cls(
            path=source,
            format_version=1,
            minecraft_version=minecraft_version,
            data_version=data_version,
            generated_at=raw.get("generated_at"),
            namespaces=dict(namespaces),
            blocks=blocks,
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "source": str(self.path),
            "format_version": self.format_version,
            "minecraft_version": self.minecraft_version,
            "data_version": self.data_version,
            "generated_at": self.generated_at,
            "block_count": len(self.blocks),
            "state_count": sum(int(entry["state_count"]) for entry in self.blocks.values()),
            "namespaces": dict(self.namespaces),
        }


def resolve_registry_path(explicit: str | Path | None = None) -> Path | None:
    """Resolve a registry path from an explicit value or MCBUILD_SERVER_REGISTRY."""
    if explicit is not None:
        return Path(explicit).expanduser()
    env_value = os.getenv(REGISTRY_ENV)
    return Path(env_value).expanduser() if env_value else None
