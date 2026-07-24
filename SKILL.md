---
name: agent-session-vault-sync
description: Inspect, incrementally archive, verify, and safely restore common AI coding applications' native local sessions in a user-selected portable Agent Session Vault. Uses independent evidence-backed adapters, precise file patterns, stable app/machine folders, SQLite online snapshots, duplicate detection, conflict preservation, non-destructive synchronization, capability-gated native restore, and a local desktop Vault console using a versioned Sidecar protocol. Use when the user asks to back up, migrate, synchronize, inspect, verify, restore, manage, search, repair, export, analyze, or extend support for coding-agent session history.
---

# Agent Session Vault

## Goal

Protect supported coding applications' native session history in a user-selected internal disk, external disk, or mounted storage without modifying active source data, and provide evidence-backed isolated recovery where supported.

The monorepo contains:

```text
ai-session/
├── desktop/                  Tauri / React / Rust desktop application
├── scripts/session_vault/    Python Vault Core
├── tests/
├── docs/
└── references/
```

The deterministic CLI remains:

```text
scripts/vault_sync.py
```

Do not replace it with improvised copy commands. If it fails, report the exact failure instead of silently falling back.

## Architecture

1. CCHV-derived Rust Providers read native sessions for viewing, search, and statistics.
2. Python adapters under `scripts/session_vault/adapters/` define native roots, exact transcript/session patterns, SQLite files, indexes, exclusions, stable IDs, and optional restore strategies.
3. Python Vault Core performs initialization, folder creation, incremental synchronization, SHA-256 comparison, SQLite snapshots, conflict preservation, reports, locking, verification, and restore.
4. Rust Sidecar Bridge starts the Python Core without a shell, validates JSONL Protocol v1, manages cancellation and timeout, and emits Tauri events.
5. React Vault Console configures operations and displays progress, errors, results, reports, and recovery actions.

Never put vendor-specific storage rules in the shared Core or recreate the backup implementation in Rust.

## Development stages

The project has five large stages. The unique status source is:

```text
docs/DEVELOPMENT_STAGE_STATUS.md
```

Current state:

```text
Stage 0: completed
Stage 1: online implementation complete; Windows automatic and manual desktop acceptance pending
Stages 2–4: not started
```

Every development response must begin with the current stage and remaining stages. Work continuously through the entire stage rather than stopping at internal task-package boundaries. Never mark a stage complete without its Definition of Done.

## Stage 1 desktop baseline

The desktop Vault Console is available at:

```text
Settings → Session Vault
```

Implemented online:

- supported application discovery;
- Vault Root, machine ID, and optional source override;
- inspect and layout preview;
- backup dry-run and real incremental sync;
- integrity verification;
- Codex single-session/full restore dry-run and real isolated restore;
- real-time progress, cancellation, timeout, structured errors, events, and report paths;
- five existing languages.

Sidecar runtime:

```text
Default Python: python
Override Python: AI_SESSION_VAULT_PYTHON
Override Sidecar: AI_SESSION_VAULT_SIDECAR
Protocol: ai-session-vault-sidecar v1
```

Stage 1 is not complete until this passes on the real Windows checkout:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

The result must be `passed-complete` with `ui_accepted: true` in `docs/PHASE_1_LOCAL_VALIDATION.json`.

## Supported applications

Discover the live list:

```bash
python scripts/vault_sync.py --mode list-apps
```

Current adapters:

- Transcript/session artifacts: `codex`, `claude-code`, `gemini-cli`, `qwen-code`, `kimi-cli`.
- Shared SQLite snapshot: `opencode`, `goose`, `hermes-agent`.
- Project rolling history: `aider`.

Read `references/common-adapters.md` before changing an adapter or claiming restore capability. A SQLite snapshot adapter preserves the full vendor database but does not provide row-level session copy/delete. Aider preserves rolling project history, not one native file per session.

## Inputs

Resolve:

- `app_id`: adapter ID or alias;
- `vault_root`: exact user-selected Vault directory;
- `source_root`: optional native source override;
- `machine_id`: optional stable human-readable machine ID;
- `mode`: `inspect`, `layout`, `sync`, `verify`, `restore`, or `list-apps`;
- `dry_run`: preflight without writes;
- restore-only: `restore_root`, `restore_scope`, and optional `session_id`;
- Sidecar-only: `output_format=jsonl`, `protocol_version`, `request_id`.

Machine ID priority:

1. `--machine-id`
2. `AGENT_VAULT_MACHINE_ID`
3. deterministic host-derived fallback

Recommend an explicit machine ID for removable drives used across reinstalls or host renames.

## Folder rules

The user supplies only `<vault-root>`. The Core builds:

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

- adapter defines `app_id`, collections, exact patterns, SQLite/index files, exclusions, and restore capability;
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

Review the resolved source, exact artifact count, SQLite/index files, sensitive exclusions, and planned machine folder. If expected native files are absent, do not run sync.

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

Do not report success unless verification returns `ok: true`. In Sidecar mode, `ok: false` emits `VERIFY_FAILED`.

## Codex isolated restore

Only adapters declaring a tested `restore_strategy` may restore. Codex currently supports isolated rollout backfill.

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

Full restore:

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

- destination must not exist and must be outside active source and Vault machine directories;
- verify selected archive hashes before writing;
- write to a temporary sibling and publish by atomic rename;
- never restore `auth.json`, credentials, or old state SQLite;
- let Codex create a fresh database and backfill from rollout files;
- create launchers and `restore-report.json`;
- never claim success unless published output and report agree.

See `references/codex-restore.md`.

## Transcript and artifact rules

Logical identity:

```text
app_id + machine_id + native_session_or_artifact_id
```

Content identity is SHA-256 of file bytes.

Apply in order:

1. unchanged size/timestamp and destination exists: skip;
2. same logical identity and hash: skip exact duplicate;
3. existing archive is an exact byte prefix: atomically update growing transcript;
4. same logical identity with divergent bytes: preserve old revision under `conflicts/`;
5. different identities with same hash: retain both and mark duplicate content;
6. missing source file: retain the archive copy.

Never delete or hard-link duplicate native files because vendor indexes may reference both identities.

## SQLite and index rules

- Never merge vendor SQLite databases.
- Never insert transcript files into a vendor database.
- Use SQLite online Backup API.
- Explicitly close database handles before publishing on Windows.
- Run `PRAGMA quick_check` before publishing.
- Keep the current snapshot under `metadata/latest/`.
- Preserve previous snapshots under `metadata/history/<timestamp>/`.
- Copy indexes atomically; never concatenate vendor indexes.
- Treat `manifest.json` as the Vault catalog.

## Cancellation and locking

- Rust cancellation and timeout kill the Sidecar child process.
- A killed process may not execute Python `finally`.
- Vault locks store the owning PID.
- The next operation immediately reclaims a lock if the PID no longer exists.
- A lock owned by an active process remains protected.
- Failure, timeout, cancellation, protocol error, or missing terminal event must never be reported as success.

## Source safety

Treat source storage as read-only. Never:

- edit or rebuild source SQLite/indexes without an explicit capability-gated repair plan;
- delete native sessions;
- copy login credentials, API keys, OAuth/token files, keychain exports, or `.env` files;
- copy logs, caches, runtime state, worktree sidecars, tool outputs, or project source unless the adapter proves they are required session artifacts.

## Development and testing policy

Development must not create or trigger GitHub Actions unless the user explicitly authorizes it.

Local checks:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
python scripts/phase1_smoke.py
```

Full Stage 1 Windows validation:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

Do not add files under `.github/workflows/`, rerun workflows, or use remote CI as a substitute for local validation. Destructive tests must use temporary HOME, source, Vault, and restore directories.

## Adding or reviewing an adapter

Follow:

- `references/adapter-contract.md`
- `references/common-adapters.md`
- `docs/FULL_DEVELOPMENT_PLAN.md`

Use upstream source or official documentation as evidence. Add sanitized tests for root resolution, precise file selection, stable IDs, repeated sync, append, conflict, duplicates, SQLite snapshots, verification, progress, and restore when declared.

Proprietary applications without a stable public storage contract remain deferred until a read-only inventory from a real installation is available.

## Required result report

After synchronization or restore report:

- adapter/app and machine ID;
- source, Vault, and target folder;
- scanned, copied, skipped, selected, restored, duplicate, and conflict counts;
- metadata updated, skipped, failed, or deliberately excluded;
- warnings;
- verification result;
- report location;
- whether the result came from CLI or Sidecar UI.
