from __future__ import annotations

import os
from pathlib import Path

from session_vault.models import AdapterSpec, SessionCollection
from session_vault.registry import register_adapter

from ._shared import extract_structured_session_id


def _extract_qwen_session_artifact_id(path: Path) -> str:
    session_id = extract_structured_session_id(path)
    state = "archived" if path.parent.name == "archive" else "active"
    return f"{session_id}:{state}"


@register_adapter("qwen-code", "qwen", "qwencode")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(
        source_root
        or os.getenv("QWEN_RUNTIME_DIR")
        or os.getenv("QWEN_HOME")
        or Path.home() / ".qwen"
    ).expanduser().resolve()
    return AdapterSpec(
        app_id="qwen-code",
        display_name="Qwen Code",
        aliases=("qwen-code", "qwen", "qwencode"),
        source_root=root,
        collections=(
            SessionCollection(
                "project_chats",
                root,
                suffixes=(".jsonl",),
                include_patterns=(
                    "projects/*/chats/*.jsonl",
                    "projects/*/chats/archive/*.jsonl",
                    "tmp/*/chats/*.jsonl",
                    "tmp/*/chats/archive/*.jsonl",
                ),
            ),
        ),
        excluded_names=(
            "oauth_creds.json",
            "mcp-oauth-tokens.json",
            "google_accounts.json",
        ),
        session_id_extractor=_extract_qwen_session_artifact_id,
    )
