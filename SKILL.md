---
name: agent-session-vault-sync
description: Incrementally archive this AI coding application's native local sessions to a user-selected portable disk, including its latest SQLite or index snapshots, while detecting duplicates and never modifying the source. Use when the user asks to back up, migrate, synchronize, inspect, verify, or deduplicate Codex, Claude Code, or another supported agent's local session history.
---

# Agent Session Vault Sync

## Goal

Archive the current AI coding application's own native session data into a portable **Agent Session Vault** selected by the user.

The workflow must:

1. Identify the current host application and its native storage mechanism.
2. Locate that application's matching folder inside the selected vault.
3. Incrementally copy new or changed session files.
4. Save the latest consistent SQLite and index snapshots without attempting to merge vendor databases.
5. Detect exact duplicates, growing active sessions, and divergent conflicts.
6. Produce a machine-readable and human-readable sync report.

## Required helper

Use `scripts/vault_sync.py` for inspection, synchronization, verification, hashing, locking, atomic writes, and SQLite snapshots.

Do not replace deterministic script behavior with improvised shell copy commands unless the helper cannot run. If the helper fails, stop and report the exact failure. Do not silently fall back to unsafe copying.

## Supported applications in V0.1

- `codex`
- `claude-code`

For any other application, do not guess and do not copy files yet. First inspect its documented and observed local storage, then prepare a new adapter proposal following `references/adapter-contract.md`.

## Inputs

Resolve these inputs before synchronization:

- `app_id`: the application currently running this skill.
- `vault_root`: the user-selected root directory on an internal disk, external disk, or mounted storage.
- `source_root`: optional override for the application's native data directory.
- `mode`: `inspect`, `sync`, or `verify`.

The user may provide the vault as a Windows drive path or Linux mount path. Always use the exact path supplied by the user. Do not hard-code a drive letter.

## Host application identification

Identify the host application from reliable runtime evidence and conversation context.

Examples:

- In Codex, use `app_id=codex`.
- In Claude Code, use `app_id=claude-code`.

If application identity is ambiguous, run inspection only. Do not synchronize under a guessed application name.

## Source rules

Treat all native application storage as read-only.

Never:

- edit the source SQLite database;
- rebuild the source application's index;
- delete source sessions;
- copy authentication tokens or API credentials;
- copy caches, logs, generated worktrees, or unrelated temporary data by default.

For Codex, default source-root resolution is:

1. Explicit `--source-root`, when supplied.
2. `CODEX_HOME`, when set.
3. `~/.codex`.

The Codex adapter archives:

- `sessions/**/*.jsonl`
- `archived_sessions/**/*.jsonl`
- `state_*.sqlite` as consistent snapshots
- `session_index.jsonl`
- `external_agent_session_imports.json`, when present

It excludes authentication and diagnostic-log databases by default.

## Vault discovery and layout

The selected root is a vault when it contains `vault.json`. If the root is empty and writable, the helper may initialize it.

Use this layout:

```text
AgentSessionVault/
├── vault.json
└── apps/
    └── <app_id>/
        └── machines/
            └── <machine_id>/
                ├── native/
                │   ├── sessions/
                │   ├── archived_sessions/
                │   └── projects/
                ├── metadata/
                │   ├── latest/
                │   └── history/
                ├── conflicts/
                ├── reports/
                └── manifest.json
```

The database and index snapshot are **per application and per source machine**. Never let a second computer overwrite another computer's latest database snapshot.

## Workflow

### 1. Inspect

Always inspect before the first synchronization on a machine or after an application upgrade that may have changed storage format.

Run:

```bash
python scripts/vault_sync.py --app <app_id> --mode inspect
```

Review:

- resolved source root;
- session categories and counts;
- detected SQLite files;
- detected index files;
- excluded sensitive files.

If inspection finds no source root or no plausible session files, stop. Do not initialize a misleading empty archive.

### 2. Dry run

Before the first real synchronization to a vault, run:

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode sync \
  --vault-root "<vault_root>" \
  --dry-run
```

Summarize the planned source, destination, session count, metadata files, and exclusions.

### 3. Synchronize

After a valid inspection and dry run, run:

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode sync \
  --vault-root "<vault_root>"
```

When `source_root` is overridden, add:

```text
--source-root "<source_root>"
```

### 4. Verify

After synchronization, run:

```bash
python scripts/vault_sync.py \
  --app <app_id> \
  --mode verify \
  --vault-root "<vault_root>"
```

Do not report success when verification reports a missing file or hash mismatch.

## Incremental session synchronization

Use the manifest to avoid copying every historical file on every run.

The logical identity of a session is:

```text
app_id + machine_id + native_session_id
```

The content identity is:

```text
SHA-256 of the session file bytes
```

Do not use title, project path, modification time, date folder, or filename alone as a unique identity.

### Duplicate rules

Apply these rules in order:

1. **Same logical identity, unchanged size and modification timestamp, destination exists**
   - Skip without hashing again.

2. **Same logical identity and same SHA-256**
   - Skip as an exact duplicate.
   - Refresh only manifest observation metadata.

3. **Same logical identity and the old archived file is an exact byte prefix of the source**
   - Treat as an active session that has grown.
   - Atomically replace the archived current version.
   - Increment its revision number.

4. **Same logical identity but divergent bytes**
   - Do not silently overwrite history.
   - Copy the old archived revision into `conflicts/<session_id>/`.
   - Atomically save the new source as the current revision.
   - Mark the event as `conflict-replaced` in the manifest and report.

5. **Different logical identities but identical SHA-256**
   - Mark as duplicate content.
   - Keep both native paths in V0.1 so a later native restore remains possible.
   - Do not automatically delete or hard-link them.

6. **Source file disappeared since the previous sync**
   - Do not delete it from the vault.
   - A backup archive is append/update, not a destructive mirror.

## SQLite handling

A vendor SQLite database represents machine-level state, not one independent session file.

Therefore:

- Never attempt to merge two SQLite databases.
- Never insert individual copied sessions into the archived vendor database.
- Keep only the latest consistent snapshot under `metadata/latest/`.
- Before replacing a changed latest snapshot, preserve the previous snapshot under `metadata/history/`.
- Prefer the SQLite online backup API.
- Run `PRAGMA quick_check` on the new snapshot before publishing it.
- Write through a temporary file and atomically rename it into place.
- If a consistent snapshot cannot be produced, leave the previous snapshot unchanged and report failure.

The transcript files and the database/index snapshot are synchronized in the same run, but they remain separate archive components.

## Index handling

Copy index files atomically.

Do not append two vendor indexes together and do not deduplicate their lines independently unless a specific adapter defines a verified reconstruction procedure.

The vault's own `manifest.json` is the authoritative archive catalog. Vendor indexes are preserved as snapshots for future restore and inspection.

## Multi-computer behavior

The same external disk may be used by multiple computers.

Each source computer must have a stable machine ID. The helper derives one automatically, or the user can set:

```text
AGENT_VAULT_MACHINE_ID
```

Use a human-readable stable override when the computer hostname may change.

Never store multiple computers' state databases in one shared `metadata/latest/` folder.

## Concurrency and removable-drive safety

Before writing, acquire the per-app/per-machine `.sync.lock`.

Do not run two synchronization processes against the same app-machine folder at the same time.

All manifest, index, session replacement, and database publication operations must use temporary files followed by atomic rename.

If the removable disk disconnects or runs out of space:

- stop the run;
- keep previously published files unchanged when possible;
- do not mark the run successful;
- leave a clear error report.

## Security

Do not archive these by default:

- `auth.json` or equivalent login credentials;
- API keys and token files;
- keychain or credential-store exports;
- diagnostic logs unless the user explicitly requests them;
- project source code outside session transcripts;
- generated worktrees and caches.

Before showing a report, avoid printing full secret-bearing source content. Paths may be shown, but redact obvious tokens in command output.

## Deletion boundary

This skill synchronizes and verifies archives. It does not permanently delete native sessions.

A later cleanup workflow may classify archived sessions, but deletion must operate through a separate review/trash process and must not directly edit a vendor SQLite snapshot.

## Required result report

After every run, report:

- application and machine ID;
- resolved source root and vault root;
- sessions scanned;
- new or updated sessions copied;
- unchanged sessions skipped;
- duplicate-content detections;
- conflict revisions preserved;
- SQLite/index snapshots updated, skipped, or failed;
- verification result;
- warnings and exact paths to the latest report.

Never say “all backed up” unless the script completed successfully and verification passed.

## Acceptance criteria

The workflow is correct only when all of these are true:

1. Re-running without source changes copies no session content again.
2. Appending messages to an existing session updates only that logical session.
3. An already copied session with the same hash is skipped.
4. Divergent content with the same native session ID preserves the earlier revision.
5. A second computer stores its database and index snapshots in a separate machine folder.
6. A source deletion does not erase the vault copy.
7. No authentication file is copied by default.
8. SQLite snapshots pass integrity verification.
9. `verify` returns no missing files or hash mismatches.
