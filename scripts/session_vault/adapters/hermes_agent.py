from __future__ import annotations

import os
from pathlib import Path

from session_vault.models import AdapterSpec
from session_vault.registry import register_adapter

from ._shared import extract_jsonl_session_id


@register_adapter("hermes-agent", "hermes")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(
        source_root or os.getenv("HERMES_HOME") or Path.home() / ".hermes"
    ).expanduser().resolve()
    return AdapterSpec(
        app_id="hermes-agent",
        display_name="Nous Hermes Agent",
        aliases=("hermes-agent", "hermes"),
        source_root=root,
        collections=(),
        sqlite_patterns=("state.db",),
        excluded_names=("auth.json", ".env"),
        session_id_extractor=extract_jsonl_session_id,
    )
