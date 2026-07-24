---
name: agent-session-vault-sync
description: Inspect, incrementally archive, verify, and safely restore common AI coding applications' native local sessions in a user-selected portable Agent Session Vault. Uses independent evidence-backed adapters, precise file patterns, stable app/machine folders, SQLite online snapshots, duplicate detection, conflict preservation, non-destructive synchronization, and capability-gated native restore. Use when the user asks to back up, migrate, synchronize, inspect, verify, restore, manage, search, repair, export, analyze, or extend support for coding-agent session history.
---

# Agent Session Vault Sync

## Goal

Archive a supported coding application's native session history to a user-selected internal disk, external disk, or mounted storage without modifying the source application, and provide evidence-backed isolated recovery where the adapter supports it.

Use the deterministic helper:

```text
scripts/vault_sync.py
```

Do not replace it with improvised copy commands. If it fails, report the exact failure instead of silently falling back.

## Architecture

1. Independent adapters under `scripts/session_vault/adapters/` define one application's native source root, exact transcript/session-artifact patterns, SQLite files, indexes, exclusions, stable IDs, and optional restore strategy.
2. The shared core performs vault initialization, folder creation, incremental synchronization, SHA-256 comparison, SQLite snapshots, conflict preservation, reports, locking, and verification.
3. The restore engine creates a new isolated application home and never writes into the active source directory by default.

Never put vendor-specific storage rules in the shared core.

## Product development baseline

The complete implementation plan for the management UI, safe session modification, cross-machine handoff, reliability, normalized parsing, usage statistics, health checks and repair, global search, readable export, and AI analysis is:

```text
docs/FULL_DEVELOPMENT_PLAN.md
```

Use that document as the architecture and sequencing baseline before adding these product modules. The raw vendor archive remains immutable; search indexes, exports, AI analyses, statistics, and repair outputs are derived and rebuildable.

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
- restore-only: `restore_root`, `restore_scope`, and optional `session_id`.

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

Only adapters declaring a tested `restore_strategy` may use `--mode restore`. Codex currently supports isolated rollout backfill.

Single-session dry run:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope session \
  --session-id "<thread-uuid>" \
  --vault-root "<vault_root>" \
  --machine-id "<machine_id>" \
  --restore-root "<new-empty-path>" \
  --dry-run
```

Full isolated restore:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope full \
  --vault-root "<vault_root>" \
  --machine-id "<machine_id>" \
  --restore-root "<new-empty-path>"
```

Restore rules:

- `restore_root` must not already exist;
- it must be outside both the active source and vault machine directory;
- verify every selected archive hash before writing;
- write to a temporary sibling and publish by atomic rename;
- never restore `auth.json` or credentials;
- never activate old state SQLite snapshots in the isolated restore;
- let Codex create a fresh state DB and backfill from rollout files;
- a single archived session is restored as active so it can be resumed;
- create launchers and `restore-report.json`;
- never claim success unless published output and report agree.

See `references/codex-restore.md`.

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

- edit/rebuild source SQLite or indexes without an explicit capability-gated repair plan;
- delete native sessions;
- copy login credentials, API keys, token files, keychain exports or `.env` files;
- copy logs, caches, runtime status, worktree sidecars, tool outputs or project source code unless an adapter explicitly proves they are required session artifacts.

## Development and testing policy

Development must not create or trigger GitHub Actions unless the user explicitly authorizes it.

Use local checks:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
```

Do not add files under `.github/workflows/`, rerun workflows, or use remote CI as a substitute for local validation. Destructive tests must use temporary HOME, source, vault, and restore directories.

## Adding or reviewing an adapter

Follow:

- `references/adapter-contract.md`
- `references/common-adapters.md`
- `docs/FULL_DEVELOPMENT_PLAN.md` for future management, parsing, search, health, repair, export, usage, handoff, and AI capabilities

Use upstream source code or official documentation as evidence. Add realistic sanitized tests for source-root resolution, precise file selection, stable IDs, repeated sync, append, conflict, duplicates, SQLite snapshots, verification, and restore when declared.

Proprietary applications without a stable public storage contract must remain deferred until a read-only inventory from a real installation is available.

## Required result report

After synchronization or restore report:

- adapter/app and machine ID;
- source, vault, and exact target folder;
- session/artifact files scanned, copied, skipped, selected, or restored;
- duplicate-content and conflict counts;
- metadata updated, skipped, failed, or deliberately excluded;
- warnings;
- verification result;
- report location.
