---
name: agent-session-vault-sync
description: Inspect, incrementally archive, verify, and safely restore supported AI coding applications' native local sessions in a user-selected portable Agent Session Vault. Uses independent evidence-backed adapters, precise file patterns, stable app/machine folders, SQLite online snapshots, duplicate detection, conflict preservation, non-destructive synchronization, and capability-gated isolated restore. Use when the user asks to back up, migrate, synchronize, inspect, verify, restore, or extend support for coding-agent session history.
---

# Agent Session Vault Sync

## Goal

Archive a supported coding application's native session history to a user-selected internal disk, external disk, or mounted storage without modifying the source application. Where an adapter explicitly supports restore, recover into a new isolated application directory rather than overwriting the active installation.

Use the deterministic helper:

```text
scripts/vault_sync.py
```

Do not replace it with improvised copy commands. If it fails, report the exact failure instead of silently falling back.

## Architecture

1. Independent adapters under `scripts/session_vault/adapters/` define one application's native source root, exact transcript/session-artifact patterns, SQLite files, indexes, exclusions, stable IDs, and optional restore strategy.
2. The shared core performs vault initialization, folder creation, incremental synchronization, SHA-256 comparison, SQLite snapshots, conflict preservation, reports, locking, verification, and isolated restore.

Never put vendor-specific storage or restore rules in the shared core without an adapter capability declaration.

## Supported applications

Discover the live list:

```bash
python scripts/vault_sync.py --mode list-apps
```

V0.3 adapters:

- Transcript/session artifacts: `codex`, `claude-code`, `gemini-cli`, `qwen-code`, `kimi-cli`.
- Shared SQLite snapshot: `opencode`, `goose`, `hermes-agent`.
- Project rolling history: `aider`.

Read `references/common-adapters.md` before changing an adapter or claiming restore capability. A SQLite snapshot adapter preserves the full vendor database but does not provide row-level per-session copy/delete. Aider preserves rolling project history, not one native file per session.

## Inputs

Resolve:

- `app_id`: adapter ID or alias;
- `vault_root`: exact directory selected by the user;
- `source_root`: optional native source override;
- `machine_id`: optional stable human-readable machine ID;
- `mode`: `inspect`, `layout`, `sync`, `verify`, `restore`, or `list-apps`;
- `restore_root`: required new isolated directory for restore;
- `restore_scope`: `session` or `full`;
- `session_id`: required for single-session restore.

Machine ID priority:

1. `--machine-id`
2. `AGENT_VAULT_MACHINE_ID`
3. deterministic host-derived fallback

Recommend an explicit machine ID for removable drives used across reinstalls or host renames.

## Folder rules

The user supplies only `<vault-root>`. The tool builds:

```text
<vault-root>/
├── vault.json
└── apps/
    └── <app_id>/
        └── machines/
            └── <machine_id>/
                ├── machine.json
                ├── manifest.json
                ├── native/<collection>/...
                ├── metadata/latest/
                ├── metadata/history/<timestamp>/
                ├── conflicts/<session_or_artifact_id>/
                └── reports/
```

Rules:

- `app_id` and collection names come from the adapter;
- transcript paths remain relative to the native collection root;
- SQLite and indexes are isolated per app and machine;
- never initialize a non-empty directory without a valid `vault.json`;
- source deletion never deletes an archive copy.

## Required archive workflow

### 1. Confirm support

```bash
python scripts/vault_sync.py --mode list-apps
```

For unsupported applications, stop and prepare an evidence-backed adapter. Do not guess paths or database semantics.

### 2. Inspect

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode inspect \
  [--source-root "<source_root>"] \
  [--vault-root "<vault_root>"] \
  [--machine-id "<machine_id>"]
```

Review:

- resolved source root;
- exact transcript/session-artifact count;
- detected SQLite and indexes;
- excluded sensitive files;
- planned app/machine folder.

If expected native files are absent, do not run sync. For Goose, use `goose info` or an explicit `--source-root` when automatic platform discovery finds no database. For Aider, point `--source-root` at the intended repository when not running from it.

### 3. Preview layout

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode layout \
  --vault-root "<vault_root>" \
  [--machine-id "<machine_id>"]
```

### 4. Dry run

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode sync \
  --vault-root "<vault_root>" \
  [--source-root "<source_root>"] \
  [--machine-id "<machine_id>"] \
  --dry-run
```

### 5. Synchronize

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode sync \
  --vault-root "<vault_root>" \
  [--source-root "<source_root>"] \
  [--machine-id "<machine_id>"]
```

### 6. Verify

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode verify \
  --vault-root "<vault_root>" \
  [--machine-id "<machine_id>"]
```

Do not report success unless verification returns `ok: true`.

## Codex isolated restore workflow

Only use restore when the adapter reports a restore strategy. V0.3 supports Codex rollout backfill restore.

### Single-session dry run

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope session \
  --session-id "<thread-uuid>" \
  --vault-root "<vault_root>" \
  --machine-id "<machine_id>" \
  --restore-root "<new_restore_root>" \
  --dry-run
```

### Publish single-session restore

Run the same command without `--dry-run` only after reviewing the plan.

### Full isolated restore

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope full \
  --vault-root "<vault_root>" \
  --machine-id "<machine_id>" \
  --restore-root "<new_restore_root>"
```

Restore safety:

- `restore_root` must not already exist;
- it must be outside the active source directory and vault machine directory;
- verify all selected archive hashes before writing;
- publish through a temporary sibling directory and atomic rename;
- never restore `auth.json`, tokens, caches, or old state SQLite automatically;
- for single-session restore, move an archived rollout into the active `sessions/` tree;
- let Codex create a fresh database and backfill metadata from rollout files;
- generate Windows/POSIX launchers, marker, README, and `restore-report.json`;
- never modify the active Codex directory or archive.

Read `references/codex-restore.md` before changing restore behavior.

## Transcript and artifact rules

Logical identity is:

```text
app_id + machine_id + native_session_or_artifact_id
```

Content identity is SHA-256 of the file bytes.

Apply in order:

1. Unchanged size/timestamp and destination exists: skip without rehashing.
2. Same logical identity and hash: skip exact duplicate.
3. Existing archive is an exact byte prefix of source: active transcript grew; atomically update and increment revision.
4. Same logical identity with divergent bytes: preserve old revision under `conflicts/`, then publish new current content.
5. Different identities with same hash: retain both and mark duplicate content.
6. Missing source file: retain archive copy.

For multi-file sessions, adapters must return distinct stable artifact IDs, such as `<session_id>:context.jsonl` and `<session_id>:state.json`.

Do not automatically delete or hard-link duplicate native files because vendor indexes or databases may reference both identities.

## SQLite and index rules

- Never merge vendor SQLite databases.
- Never insert transcript files into a vendor database.
- Use SQLite online backup API.
- Run `PRAGMA quick_check` before publishing.
- Keep the current snapshot in `metadata/latest/`.
- Preserve the previous snapshot in `metadata/history/<timestamp>/`.
- Copy indexes atomically; never concatenate vendor indexes.
- Treat `manifest.json` as the vault catalog.

## Source safety

Treat source storage as read-only. Never:

- edit/rebuild source SQLite or indexes;
- delete native sessions;
- copy login credentials, API keys, token files, keychain exports or `.env` files;
- copy logs, caches, runtime status, worktree sidecars, tool outputs or project source code unless an adapter explicitly proves they are required session artifacts.

## Development validation policy

Do not add or trigger GitHub Actions during active development unless the user explicitly requests it. Run validation manually:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
```

Record the commands and results in the development report or PR description. Do not claim automatic CI coverage when no workflow is installed.

## Adding or reviewing an adapter

Follow:

- `references/adapter-contract.md`
- `references/common-adapters.md`

Use upstream source code or official documentation as evidence. Add realistic sanitized tests for source-root resolution, precise file selection, stable IDs, repeated sync, append, conflict, duplicates, SQLite snapshots, verification, and any declared native restore strategy.

Proprietary applications without a stable public storage contract must remain deferred until a read-only inventory from a real installation is available.

## Required result report

After synchronization report:

- adapter/app and machine ID;
- source, vault, and exact machine folder;
- session/artifact files scanned, copied and skipped;
- duplicate-content and conflict counts;
- metadata updated, skipped and failed;
- warnings;
- verification result and report location.

After restore report:

- adapter/app, machine, scope, and session ID when applicable;
- archive machine root and isolated restore root;
- selected/restored session count;
- restored indexes and skipped SQLite snapshots;
- activated archived session count;
- launchers and report path;
- warnings and first-launch database rebuild requirement.
