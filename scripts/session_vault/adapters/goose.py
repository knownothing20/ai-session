from __future__ import annotations

import os
import platform
from pathlib import Path

from session_vault.models import AdapterSpec
from session_vault.registry import register_adapter

from ._shared import extract_jsonl_session_id


def _existing_or_default(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if (candidate / "sessions" / "sessions.db").exists():
            return candidate
    return candidates[0]


def _default_data_root() -> Path:
    path_root = os.getenv("GOOSE_PATH_ROOT")
    if path_root:
        return Path(path_root).expanduser().resolve() / "data"
    home = Path.home()
    system = platform.system().lower()
    if system == "darwin":
        candidates = [home / "Library" / "Application Support" / "Block" / "goose"]
    elif system == "windows":
        appdata = Path(os.getenv("APPDATA") or home / "AppData" / "Roaming")
        local = Path(os.getenv("LOCALAPPDATA") or home / "AppData" / "Local")
        candidates = [appdata / "Block" / "goose", local / "Block" / "goose"]
    else:
        xdg_data = Path(os.getenv("XDG_DATA_HOME") or home / ".local" / "share")
        candidates = [xdg_data / "goose", xdg_data / "Block" / "goose"]
    return _existing_or_default(candidates).resolve()


@register_adapter("goose", "block-goose", "aaif-goose")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(source_root).expanduser().resolve() if source_root else _default_data_root()
    return AdapterSpec(
        app_id="goose",
        display_name="Goose",
        aliases=("goose", "block-goose", "aaif-goose"),
        source_root=root,
        collections=(),
        sqlite_patterns=("sessions/sessions.db",),
        session_id_extractor=extract_jsonl_session_id,
    )
