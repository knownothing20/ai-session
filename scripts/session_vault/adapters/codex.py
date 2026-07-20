from __future__ import annotations

import os
from pathlib import Path

from session_vault.models import AdapterSpec, SessionCollection
from session_vault.registry import register_adapter

from ._shared import extract_jsonl_session_id


@register_adapter("codex", "openai-codex")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(
        source_root or os.getenv("CODEX_HOME") or Path.home() / ".codex"
    ).expanduser().resolve()
    return AdapterSpec(
        app_id="codex",
        display_name="OpenAI Codex",
        aliases=("codex", "openai-codex"),
        source_root=root,
        collections=(
            SessionCollection("sessions", root / "sessions"),
            SessionCollection("archived_sessions", root / "archived_sessions"),
        ),
        sqlite_patterns=("state_*.sqlite", "state.sqlite"),
        index_files=("session_index.jsonl", "external_agent_session_imports.json"),
        excluded_names=("auth.json", "logs_2.sqlite"),
        session_id_extractor=extract_jsonl_session_id,
    )
