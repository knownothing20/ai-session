from __future__ import annotations

import os
from pathlib import Path

from session_vault.models import AdapterSpec
from session_vault.registry import register_adapter

from ._shared import extract_jsonl_session_id


def _default_data_root() -> Path:
    xdg_data = os.getenv("XDG_DATA_HOME")
    base = Path(xdg_data).expanduser() if xdg_data else Path.home() / ".local" / "share"
    return base / "opencode"


@register_adapter("opencode", "open-code")
def build(source_root: str | None = None) -> AdapterSpec:
    db_override = os.getenv("OPENCODE_DB")
    if source_root:
        supplied = Path(source_root).expanduser().resolve()
        if supplied.suffix == ".db":
            root, patterns = supplied.parent, (supplied.name,)
        else:
            root, patterns = supplied, ("opencode.db", "opencode-*.db")
    elif db_override:
        candidate = Path(db_override).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
            root, patterns = resolved.parent, (resolved.name,)
        else:
            root, patterns = _default_data_root().resolve(), (db_override,)
    else:
        root, patterns = _default_data_root().resolve(), ("opencode.db", "opencode-*.db")
    return AdapterSpec(
        app_id="opencode",
        display_name="OpenCode",
        aliases=("opencode", "open-code"),
        source_root=root,
        collections=(),
        sqlite_patterns=patterns,
        session_id_extractor=extract_jsonl_session_id,
    )
