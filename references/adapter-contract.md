# Adapter Contract — v0.3

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
5. `collections` — transcript or session-artifact collections.
6. `sqlite_patterns` — vendor SQLite files that require consistent snapshots.
7. `index_files` — indexes copied atomically.
8. `excluded_names` — authentication, logs, secrets, caches, and other unsafe files.
9. `session_id_extractor` — a verified function that extracts a stable logical ID.
10. `restore_strategy` — optional capability identifier for evidence-backed native restore.

A SQLite-only adapter may use an empty `collections` tuple. It must never attempt row-level merge or deletion in the vendor database.

## Session collection fields

Each `SessionCollection` defines:

- `name` — stable vault collection name;
- `root` — native root used to preserve relative paths;
- `suffixes` — allowed file suffixes;
- `include_patterns` — precise glob patterns relative to `root`;
- `exclude_patterns` — relative glob patterns that must be skipped.

Prefer exact include patterns. Do not recursively copy every `.json` file when the vendor directory also contains credentials, runtime status, logs, worktree state, tool outputs, or caches.

## Minimal transcript adapter

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
        collections=(
            SessionCollection(
                "sessions",
                root,
                suffixes=(".jsonl",),
                include_patterns=("sessions/**/*.jsonl",),
            ),
        ),
        sqlite_patterns=("state*.sqlite",),
        index_files=("index.jsonl",),
        excluded_names=("auth.json", "credentials.json"),
        session_id_extractor=extract_jsonl_session_id,
    )
```

## Multi-file native sessions

Some applications store one logical session as multiple files. Do not let these files overwrite one another in the manifest.

The extractor should return a stable artifact identity such as:

```text
<native_session_id>:<artifact_role>
```

For example, Kimi uses separate `context.jsonl`, `wire.jsonl`, and `state.json` files. The manifest keeps each artifact independently while preserving the common native session UUID in the generated identity.

## SQLite-only adapter

```python
@register_adapter("example-db-agent")
def build(source_root: str | None = None) -> AdapterSpec:
    root = Path(source_root or Path.home() / ".example-db-agent").expanduser().resolve()
    return AdapterSpec(
        app_id="example-db-agent",
        display_name="Example DB Agent",
        aliases=("example-db-agent",),
        source_root=root,
        collections=(),
        sqlite_patterns=("sessions.db",),
        session_id_extractor=extract_jsonl_session_id,
    )
```

The extractor is not used when no transcript collections exist; it is retained for a uniform adapter interface.

## Native restore capability

Restore is disabled unless an adapter explicitly declares a verified strategy:

```python
restore_strategy="vendor-specific-strategy-id"
```

A restore strategy must define and test:

- exact archive artifacts required;
- whether vendor SQLite can be restored safely or must be rebuilt;
- whether archived sessions need activation for resume;
- destination isolation rules;
- path traversal prevention;
- archive hash verification;
- staging and atomic publication;
- generated launch instructions;
- credentials and runtime state that must remain excluded.

Never infer restore support merely because transcript files were archived. See `references/codex-restore.md` for the Codex rollout-backfill implementation.

## Development validation

During active development, validation is manual unless the user explicitly requests GitHub Actions:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
```

Do not add workflow triggers by default. Record manual commands and results in the PR or development report.

## Activation checklist

Before shipping a new adapter:

- use upstream source code or official documentation as evidence;
- inspect real files produced by the target software;
- confirm whether active sessions append, rewrite, or use multiple artifacts;
- identify a stable native session or artifact ID;
- identify all SQLite files and verify the online backup API;
- identify indexes needed for future restore;
- exclude authentication, tokens, runtime sidecars, logs and caches;
- test default, environment-variable and explicit source-root resolution;
- add realistic sanitized fixtures;
- run `inspect`, first `sync`, repeated `sync`, append/update, conflict, duplicate, SQLite and `verify` tests;
- when declaring restore, add single/full restore, hash tamper, unsafe path, existing destination, dry-run, launcher and report tests.

Never guess a vendor's database schema and never insert copied transcripts into a vendor database. See `common-adapters.md` for evidence and known limitations.
