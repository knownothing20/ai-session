from __future__ import annotations

import os
from pathlib import Path

from session_vault.models import AdapterSpec, SessionCollection
from session_vault.registry import register_adapter


def _extract_kimi_artifact_id(path: Path) -> str:
    sessions_root = next((parent for parent in path.parents if parent.name == "sessions"), None)
    if sessions_root is None:
        return f"path:{path.as_posix()}"
    relative = path.relative_to(sessions_root)
    parts = relative.parts
    if len(parts) >= 3:
        session_id = parts[1]
        artifact = "/".join(parts[2:])
    elif len(parts) == 2:
        session_id = path.stem
        artifact = path.name
    else:
        session_id = path.stem
        artifact = path.name
    return f"{session_id}:{artifact}"


@register_adapter("kimi-cli", "kimi", "kimi-code")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(
        source_root or os.getenv("KIMI_SHARE_DIR") or Path.home() / ".kimi"
    ).expanduser().resolve()
    return AdapterSpec(
        app_id="kimi-cli",
        display_name="Moonshot Kimi Code CLI",
        aliases=("kimi-cli", "kimi", "kimi-code"),
        source_root=root,
        collections=(
            SessionCollection(
                "sessions",
                root,
                suffixes=(".jsonl", ".json"),
                include_patterns=(
                    "sessions/*/*.jsonl",
                    "sessions/*/*/**/*.jsonl",
                    "sessions/*/*/**/*.json",
                ),
            ),
        ),
        index_files=("kimi.json",),
        session_id_extractor=_extract_kimi_artifact_id,
    )
