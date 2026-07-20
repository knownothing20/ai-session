from __future__ import annotations

import json
import re
from pathlib import Path

UUID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def nested_session_id(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("session_id", "sessionId", "thread_id", "threadId", "conversation_id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        if value.get("type") in {"session_meta", "sessionMeta", "session"}:
            for key in ("id", "uuid"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    return candidate
        for key in ("payload", "item", "meta", "message"):
            found = nested_session_id(value.get(key))
            if found:
                return found
    elif isinstance(value, list):
        for item in value[:8]:
            found = nested_session_id(item)
            if found:
                return found
    return None


def extract_jsonl_session_id(path: Path) -> str:
    match = UUID_RE.search(path.stem)
    if match:
        return match.group(1).lower()
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for _ in range(16):
                line = stream.readline()
                if not line:
                    break
                try:
                    found = nested_session_id(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if found:
                    return found
    except OSError:
        pass
    return f"path:{path.as_posix()}"
