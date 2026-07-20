---
name: agent-session-vault-sync
description: Inspect, incrementally archive, and verify this AI coding application's native local sessions in a user-selected portable Agent Session Vault. Uses independent application adapters, stable app/machine folders, SQLite online snapshots, duplicate detection, conflict preservation, and non-destructive synchronization. Use when the user asks to back up, migrate, synchronize, inspect, verify, or extend support for Codex, Claude Code, or another coding agent's local session history.
---

# Agent Session Vault Sync

## Goal

Archive the current coding agent's native session history to a user-selected internal disk, external disk, or mounted storage without modifying the source application.

Use the deterministic helper:

```text
scripts/vault_sync.py
```

Do not replace it with improvised copy commands unless the helper cannot run. If it fails, report the exact failure instead of silently falling back.

## Architecture

The implementation has two layers:

1. Independent adapters under `scripts/session_vault/adapters/` identify one application's native source root, transcript collections, SQLite files, indexes, exclusions, and native session IDs.
2. The shared core performs vault initialization, stable folder creation, incremental synchronization, SHA-256 comparison, SQLite snapshots, conflict preservation, reports, locking, and verification.

New applications must be added as independent adapter modules following `references/adapter-contract.md`. Do not add vendor-specific storage rules to the core synchronizer.

## Supported applications

Discover current adapters rather than assuming a hard-coded list:

```bash
python scripts/vault_sync.py --mode list-apps
```

V0.2 includes Codex and Claude Code.

## Inputs

Resolve:

- `app_id`: adapter ID or alias.
- `vault_root`: exact directory selected by the user.
- `source_root`: optional native source override.
- `machine_id`: optional stable human-readable machine ID.
- `mode`: `inspect`, `layout`, `sync`, `verify`, or `list-apps`.

Machine ID priority:

1. `--machine-id`
2. `AGENT_VAULT_MACHINE_ID`
3. deterministic host-derived fallback

Recommend an explicit stable machine ID for removable drives used across reinstalls or host renames.

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
                ├── conflicts/<session_id>/
                └── reports/
```

Rules:

- `app_id` is stable and owned by the adapter.
- `<collection>` is declared by the adapter.
- transcript paths remain relative to the native collection root;
- SQLite and indexes are isolated per app and per machine;
- never initialize a non-empty directory that lacks a valid `vault.json`;
- source deletions never delete archive files.

See `references/vault-layout.md`.

## Required workflow

### 1. Discover or confirm the adapter

```bash
python scripts/vault_sync.py --mode list-apps
```

If the requested application is unsupported, stop synchronization and prepare a new adapter using the contract. Do not guess paths or database semantics.

### 2. Inspect

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode inspect \
  [--source-root "<source_root>"] \
  [--vault-root "<vault_root>"] \
  [--machine-id "<machine_id>"]
```

Review source root, collections, transcript count, SQLite files, indexes, exclusions, and the planned machine folder.

### 3. Show layout when useful

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode layout \
  --vault-root "<vault_root>" \
  [--machine-id "<machine_id>"]
```

### 4. Dry run before first synchronization

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode sync \
  --vault-root "<vault_root>" \
  [--machine-id "<machine_id>"] \
  --dry-run
```

### 5. Synchronize

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode sync \
  --vault-root "<vault_root>" \
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

Do not report success unless verification reports `ok: true`.

## Duplicate and update rules

Logical identity:

```text
app_id + machine_id + native_session_id
```

Content identity:

```text
SHA-256(file bytes)
```

Apply in order:

1. Same logical identity, unchanged size and timestamp, destination exists: skip without rehashing.
2. Same logical identity and same hash: skip exact duplicate.
3. Existing archive is an exact byte prefix of the source: active session grew; atomically update and increment revision.
4. Same logical identity but divergent bytes: preserve old revision under `conflicts/`, then publish the new current version.
5. Different logical identities but same hash: retain both native paths and mark duplicate content.
6. Missing source file: retain the archive copy.

Do not delete or hard-link duplicate native files automatically because vendor indexes or databases may reference both identities.

## SQLite and index rules

- Never merge vendor SQLite databases.
- Never insert transcript files into a vendor database.
- Use SQLite online backup API for consistent snapshots.
- Run `PRAGMA quick_check` before publishing a snapshot.
- Keep the latest snapshot under `metadata/latest/`.
- Move the previous published snapshot to `metadata/history/<timestamp>/` before replacement.
- Copy indexes atomically; never append two vendor indexes together.
- Treat the vault's `manifest.json` as the archive catalog.

## Source safety

Treat source storage as read-only. Never:

- edit or rebuild source SQLite/index files;
- delete native sessions;
- copy login credentials, API keys, keychain exports, or token files;
- copy caches, diagnostic logs, worktrees, or project source code by default.

## Adding a new adapter

Create one independent module:

```text
scripts/session_vault/adapters/<app_id>.py
```

Register it with `@register_adapter(...)`, return a complete `AdapterSpec`, and add realistic sanitized tests. The registry discovers modules automatically; do not edit a central adapter switch.

Before activation, verify real storage locations, active-session write behavior, native ID extraction, SQLite consistency, index relationships, exclusions, repeated sync, append, conflict, duplicate, and verify behavior.

## Required result report

After synchronization report:

- adapter/app ID and machine ID;
- source, vault, and exact machine folder;
- sessions scanned, copied, and skipped;
- duplicate-content and conflict counts;
- metadata updated, skipped, and failed;
- warnings;
- verification result and report location.
