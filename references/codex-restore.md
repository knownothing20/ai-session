# Codex isolated restore

Codex is the first adapter with native restore support.

The restore workflow deliberately creates a **new isolated `CODEX_HOME`**. It never writes into the active `~/.codex` directory and never changes the archive.

## Why restored SQLite snapshots are not activated automatically

The archive keeps `state_*.sqlite` snapshots for disaster analysis and same-environment recovery, but an isolated restore does not publish them into the new Codex home because:

- thread rows can retain rollout paths from the original computer;
- a completed backfill watermark can prevent newly copied older rollout files from being scanned;
- mixing one old database with a selected subset of JSONL files creates database/file parity problems.

Instead, restore copies rollout JSONL files and relevant indexes. Codex starts with no state database and rebuilds thread metadata from the restored rollouts.

Upstream evidence:

- Codex startup backfill scans both `sessions/` and `archived_sessions/`, extracts metadata from rollout files, and upserts thread rows: <https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/rollout/src/state_db_tests.rs>
- `codex doctor` recommends starting Codex with no state DB so startup backfill can create it from rollout files: <https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/cli/src/doctor/thread_inventory.rs>
- Codex supports resuming directly by thread ID: <https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/utils/cli/src/resume_command.rs>

## Single-session restore

Dry run:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope session \
  --session-id <thread-uuid> \
  --vault-root /path/to/AgentSessionVault \
  --machine-id <source-machine-id> \
  --restore-root /path/to/new-codex-recovery \
  --dry-run
```

Publish the recovery directory by removing `--dry-run`.

Behavior:

- verifies the selected transcript hash before writing;
- restores only that rollout;
- filters `session_index.jsonl` to matching entries when available;
- restores an archived selected rollout under active `sessions/` so it can be resumed;
- skips old SQLite snapshots;
- writes Windows and POSIX launchers;
- writes `.agent-session-restore.json` and `restore-report.json`.

## Full isolated restore

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode restore \
  --restore-scope full \
  --vault-root /path/to/AgentSessionVault \
  --machine-id <source-machine-id> \
  --restore-root /path/to/new-codex-recovery
```

Behavior:

- restores all current rollout copies in the manifest;
- preserves active versus archived collection layout;
- restores vendor index snapshots;
- skips old SQLite snapshots and lets Codex rebuild a fresh database.

## Launching

The restore directory contains:

```text
start-codex-recovery.cmd
start-codex-recovery.sh
README-RESTORE.txt
restore-report.json
```

Both launcher scripts set:

```text
CODEX_HOME=<restore-root>
CODEX_SQLITE_HOME=<restore-root>
```

A single-session launcher runs `codex resume <thread-id>`. A full restore launcher runs `codex resume` and opens the restored picker.

Codex may request authentication because `auth.json` is intentionally never restored.

## Safety rules

- `--restore-root` must not already exist;
- the restore root must be outside the active source and vault machine directories;
- source archive hashes must match the manifest;
- publishing uses a temporary sibling directory followed by atomic rename;
- failures remove the unpublished staging directory;
- the active Codex directory and archive remain read-only.
