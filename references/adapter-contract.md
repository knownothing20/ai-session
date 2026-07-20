# Adapter Contract — v0.2

Each application adapter is one independent Python module under:

```text
scripts/session_vault/adapters/<app_id>.py
```

The registry discovers modules automatically. A new adapter does **not** require editing the core synchronizer or a central `if/elif` switch.

## Required fields

An adapter returns an `AdapterSpec` with:

1. `app_id` — stable lowercase identifier, such as `codex` or `gemini-cli`.
2. `display_name` — human-readable software name.
3. `aliases` — accepted CLI aliases.
4. `source_root` — resolved native storage root.
5. `collections` — one or more independent transcript collections.
6. `sqlite_patterns` — vendor SQLite files that require consistent snapshots.
7. `index_files` — indexes copied atomically.
8. `excluded_names` — authentication, logs, secrets, caches, and other unsafe files.
9. `session_id_extractor` — a verified function that extracts the native session/thread ID.

## Minimal adapter example

```python
from pathlib import Path
from session_vault.models import AdapterSpec, SessionCollection
from session_vault.registry import register_adapter
from ._shared import extract_jsonl_session_id

@register_adapter("example-agent", "example")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(source_root or Path.home() / ".example-agent").expanduser().resolve()
    return AdapterSpec(
        app_id="example-agent",
        display_name="Example Agent",
        aliases=("example-agent", "example"),
        source_root=root,
        collections=(SessionCollection("sessions", root / "sessions"),),
        sqlite_patterns=("state*.sqlite",),
        index_files=("index.jsonl",),
        excluded_names=("auth.json", "credentials.json"),
        session_id_extractor=extract_jsonl_session_id,
    )
```

## Activation checklist

Before shipping a new adapter:

- inspect real files produced by the target software;
- confirm whether active sessions append or rewrite;
- identify a stable native session ID;
- identify all database sidecars and whether SQLite Backup API works;
- exclude authentication and tokens;
- add tests using realistic sanitized fixtures;
- run `inspect`, `sync`, repeated `sync`, append/update, conflict, duplicate, and `verify` tests.

Never guess a vendor's database schema and never insert copied transcripts into a vendor database.
