from __future__ import annotations

from pathlib import Path

from session_vault.models import AdapterSpec, SessionCollection
from session_vault.registry import register_adapter

from ._shared import extract_jsonl_session_id


@register_adapter("claude-code", "claude", "claudecode")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(source_root or Path.home() / ".claude").expanduser().resolve()
    return AdapterSpec(
        app_id="claude-code",
        display_name="Claude Code",
        aliases=("claude-code", "claude", "claudecode"),
        source_root=root,
        collections=(SessionCollection("projects", root / "projects"),),
        index_files=("history.jsonl",),
        session_id_extractor=extract_jsonl_session_id,
    )
