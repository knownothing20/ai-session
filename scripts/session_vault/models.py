from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class SessionCollection:
    """One native transcript or session-artifact collection owned by an adapter.

    ``include_patterns`` and ``exclude_patterns`` are evaluated relative to
    ``root``.  This lets an adapter describe exact vendor layouts without making
    the shared synchronizer guess which JSON files are real conversations.
    """

    name: str
    root: Path
    suffixes: tuple[str, ...] = (".jsonl", ".json")
    include_patterns: tuple[str, ...] = ("**/*",)
    exclude_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdapterSpec:
    """Resolved storage description for one application on this machine."""

    app_id: str
    display_name: str
    aliases: tuple[str, ...]
    source_root: Path
    collections: tuple[SessionCollection, ...]
    sqlite_patterns: tuple[str, ...] = ()
    index_files: tuple[str, ...] = ()
    excluded_names: tuple[str, ...] = ()
    session_id_extractor: Callable[[Path], str] | None = field(default=None, compare=False)
