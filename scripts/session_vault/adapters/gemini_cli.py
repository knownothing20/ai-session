from __future__ import annotations

from pathlib import Path

from session_vault.models import AdapterSpec, SessionCollection
from session_vault.registry import register_adapter

from ._shared import extract_structured_session_id


@register_adapter("gemini-cli", "gemini")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(source_root or Path.home() / ".gemini").expanduser().resolve()
    return AdapterSpec(
        app_id="gemini-cli",
        display_name="Google Gemini CLI",
        aliases=("gemini-cli", "gemini"),
        source_root=root,
        collections=(
            SessionCollection(
                "project_chats",
                root / "tmp",
                suffixes=(".jsonl", ".json"),
                include_patterns=(
                    "*/chats/session-*.jsonl",
                    "*/chats/session-*.json",
                    "*/chats/**/session-*.jsonl",
                    "*/chats/**/session-*.json",
                ),
            ),
        ),
        index_files=("projects.json",),
        excluded_names=(
            "oauth_creds.json",
            "mcp-oauth-tokens.json",
            "a2a-oauth-tokens.json",
            "google_accounts.json",
        ),
        session_id_extractor=extract_structured_session_id,
    )
