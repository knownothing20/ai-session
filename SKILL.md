---
name: agent-session-vault-sync
description: Inspect, incrementally archive, verify, and safely restore supported AI coding applications' native local sessions in a user-selected portable Agent Session Vault. Uses independent evidence-backed adapters, precise file patterns, stable app/machine folders, SQLite online snapshots, duplicate detection, conflict preservation, non-destructive synchronization, and isolated Codex recovery. Use when the user asks to back up, migrate, synchronize, inspect, verify, restore, or extend support for coding-agent session history.
---

# Agent Session Vault Sync

## Goal

Archive a supported coding application's native session history to a user-selected internal disk, external disk, or mounted storage without modifying the source application.

For adapters with an explicitly tested restore strategy, create a new isolated native application home from the archive without overwriting the active installation.

Use the deterministic helper:

```text
scripts/vault_sync.py
```

Do not replace it with improvised copy commands. If it fails, report the exact failure instead of silently falling back.

## Architecture

1. Independent adapters under `scripts/session_vault/adapters/` define one application's native source root, exact transcript/session-artifact patterns, SQLite files, indexes, exclusions, stable IDs, and optional restore strategy.
2. The shared synchronization core performs vault initialization, folder creation, incremental copy, SHA-256 comparison, SQLite snapshots, conflict preservation, reports, locking, and verification.
3. The restore engine publishes an isolated application home through a staging directory and atomic rename.

Never put vendor-specific storage discovery or restore behavior into the shared synchronizer unless it is represented by an explicit adapter capability.

## Supported applications

Discover the live list:

```bash
python scripts/vault_sync.py --mode list-apps
```

V0.3 adapters:

- Transcript/session artifacts: `codex`, `claude-code`, `gemini-cli`, `qwen-code`, `kimi-cli`.
- Shared SQLite snapshot: `opencode`, `goose`, `hermes-agent`.
- Project rolling history: `aider`.

Only `codex` currently declares a native restore strategy. Do not infer restore support merely because an adapter can archive files or snapshot SQLite.

Read:

- `references/common-adapters.md`
- `references/codex-restore.md`

A SQLite snapshot adapter preserves a complete vendor database but does not provide row-level per-session copy, deletion, or native restore. Aider preserves rolling project history, not one native file per session.

## Inputs

Resolve:

- `app_id`: adapter ID or alias;
- `vault_root`: exact archive directory selected by the user;
- `source_root`: optional native source override;
- `machine_id`: optional stable human-readable source-machine ID;
- `mode`: `inspect`, `layout`, `sync`, `verify`, `restore`, or `list-apps`;
- `restore_root`: new isolated application directory for restore;
- `restore_scope`: `session` or `full`;
- `session_id`: required for a single-session restore.

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

## Archive workflow

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
- planned app/machine folder;
- declared restore strategy, if any.

If expected native files are absent, do not run sync. For Goose, use `goose info` or explicit `--source-root` when discovery finds no database. For Aider, point `--source-root` at the intended repository when not running from it.

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

Do not report archive success unless verification returns `ok: true`.

## Codex restore workflow

Restore is intentionally isolated. Never default `--restore-root` to the active `CODEX_HOME`, `%USERPROFILE%\.codex`, or `~/.codex`.

### Single-session dry run

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope session \
  --session-id <thread-uuid> \
  --vault-root "<vault_root>" \
  --machine-id "<source_machine_id>" \
  --restore-root "<new_restore_root>" \
  --dry-run
```

Review the selected session count, archived hash verification, skipped SQLite count, and planned launch command.

### Single-session restore

Run the same command without `--dry-run`.

Expected behavior:

- require a restore path that does not already exist;
- verify the archived rollout hash before writing;
- restore only the matching rollout;
- filter `session_index.jsonl` to matching entries when available;
- publish an archived selected session under active `sessions/` so it can be resumed;
- never activate an old state SQLite snapshot;
- generate `start-codex-recovery.cmd`, `start-codex-recovery.sh`, `README-RESTORE.txt`, and `restore-report.json`.

### Full isolated restore

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope full \
  --vault-root "<vault_root>" \
  --machine-id "<source_machine_id>" \
  --restore-root "<new_restore_root>"
```

Expected behavior:

- restore every current rollout represented in the manifest;
- preserve active and archived collection layout;
- restore index snapshots;
- skip old state SQLite snapshots;
- let Codex create a fresh state database and backfill it from rollouts.

After publishing, use the generated launcher. Authentication may be requested because `auth.json` is never restored.

Never say restore succeeded unless `published` is true, restored counts match the plan, and `restore-report.json` exists.

## Transcript and artifact rules

Logical identity is:

```text
app_id + machine_id + native_session_or_artifact_id
```

Content identity is SHA-256 of file bytes.

Apply in order:

1. Unchanged size/timestamp and destination exists: skip without rehashing.
2. Same logical identity and hash: skip exact duplicate.
3. Existing archive is an exact byte prefix of source: active transcript grew; atomically update and increment revision.
4. Same logical identity with divergent bytes: preserve old revision under `conflicts/`, then publish new current content.
5. Different identities with the same hash: retain both and mark duplicate content.
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
- Do not automatically activate an archived SQLite snapshot in an isolated native restore unless a separately tested restore strategy explicitly requires it.

## Source and restore safety

Treat source storage and the vault archive as read-only during restore. Never:

- edit or rebuild source SQLite or indexes;
- delete native sessions;
- copy login credentials, API keys, token files, keychain exports, or `.env` files;
- copy logs, caches, runtime status, worktree sidecars, tool outputs, or project source code unless an adapter proves they are required session artifacts;
- restore into a path that already exists;
- restore inside the active source directory or vault machine directory;
- publish partially written recovery content.

Restore must use a temporary sibling directory followed by atomic rename. On failure, remove the unpublished staging directory.

## Adding or reviewing an adapter

Follow:

- `references/adapter-contract.md`
- `references/common-adapters.md`
- `references/codex-restore.md`

Use upstream source code or official documentation as evidence. Add realistic sanitized tests for source-root resolution, precise file selection, stable IDs, repeated sync, append, conflict, duplicates, SQLite snapshots, verification, and any declared restore strategy.

Proprietary applications without a stable public storage contract must remain deferred until a read-only inventory from a real installation is available.

## Required result report

After synchronization report:

- adapter/app and machine ID;
- source, vault, and exact machine folder;
- session/artifact files scanned, copied, and skipped;
- duplicate-content and conflict counts;
- metadata updated, skipped, and failed;
- warnings;
- verification result and report location.

After restore report:

- adapter and source machine ID;
- restore scope and requested session ID;
- selected and restored counts;
- archived sessions activated for single restore;
- indexes restored and SQLite snapshots skipped;
- restore root, launchers, and report path;
- `published` status and warnings.
