# Adapter Contract — v0.3

Each application adapter is one independent Python module under:

```text
scripts/session_vault/adapters/<app_id>.py
```

The registry discovers modules automatically. A new adapter does **not** require editing the core synchronizer or a central `if/elif` switch.

## Adapter fields

An adapter returns an `AdapterSpec` with:

1. `app_id` — stable lowercase identifier, such as `codex` or `gemini-cli`.
2. `display_name` — human-readable software name.
3. `aliases` — accepted CLI aliases.
4. `source_root` — resolved native storage root.
5. `collections` — transcript or session-artifact collections.
6. `sqlite_patterns` — vendor SQLite files that require consistent snapshots.
7. `index_files` — indexes copied atomically.
8. `excluded_names` — authentication, logs, secrets, caches, and other unsafe files.
9. `session_id_extractor` — verified function that extracts a stable logical ID.
10. `restore_strategy` — optional tested native recovery strategy. Leave `None` by default.

A SQLite-only adapter may use an empty `collections` tuple. It must never attempt row-level merge or deletion in the vendor database.

An adapter must not declare `restore_strategy` merely because its files can be copied. Native restore requires separate evidence, safety design, and tests.

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
        restore_strategy=None,
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
        restore_strategy=None,
    )
```

The extractor is not used when no transcript collections exist; it is retained for a uniform adapter interface.

## Native restore contract

A restore-capable adapter must define and test:

- whether restore is per-session, full-library, or both;
- whether old SQLite can safely be activated or must be rebuilt;
- mapping from vault collections back to native paths;
- handling for archived sessions;
- index reconstruction or filtering;
- authentication exclusions;
- isolated target-root rules;
- staging and atomic publication;
- archive hash verification and restored-file verification;
- recovery launch instructions and result report.

Restore must be disabled unless all required semantics are known. Never infer database merge or rebuild behavior from file names alone.

The current Codex strategy is:

```text
codex-rollout-backfill
```

It restores rollout JSONL and relevant indexes into a new isolated `CODEX_HOME`, skips old state SQLite, and lets Codex rebuild a fresh database from rollouts. See `codex-restore.md`.

## Activation checklist

Before shipping a new archive adapter:

- use upstream source code or official documentation as evidence;
- inspect real files produced by the target software;
- confirm whether active sessions append, rewrite, or use multiple artifacts;
- identify a stable native session or artifact ID;
- identify all SQLite files and verify the online backup API;
- identify indexes needed for future restore;
- exclude authentication, tokens, runtime sidecars, logs, and caches;
- test default, environment-variable, and explicit source-root resolution;
- add realistic sanitized fixtures;
- run `inspect`, first `sync`, repeated `sync`, append/update, conflict, duplicate, SQLite, and `verify` tests.

Before declaring restore support, additionally test:

- missing and tampered archive files;
- existing and unsafe target paths;
- dry run;
- single and full scope where supported;
- archived-session behavior;
- generated launchers;
- recovery report fields;
- no modification of source or vault.

Never guess a vendor database schema and never insert copied transcripts into a vendor database. See `common-adapters.md` for evidence and known limitations.
