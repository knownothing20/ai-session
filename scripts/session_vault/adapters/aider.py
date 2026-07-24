from __future__ import annotations

from pathlib import Path

from session_vault.models import AdapterSpec, SessionCollection
from session_vault.registry import register_adapter


def _extract_aider_history_id(path: Path) -> str:
    return path.name


@register_adapter("aider", "aider-chat")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(source_root).expanduser().resolve() if source_root else Path.cwd().resolve()
    return AdapterSpec(
        app_id="aider",
        display_name="Aider project history",
        aliases=("aider", "aider-chat"),
        source_root=root,
        collections=(
            SessionCollection(
                "project_history",
                root,
                suffixes=(".md", ".history"),
                include_patterns=(
                    ".aider.chat.history.md",
                    ".aider.input.history",
                    ".aider.llm.history",
                ),
            ),
        ),
        session_id_extractor=_extract_aider_history_id,
    )
