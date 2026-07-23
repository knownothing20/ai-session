# Agent Session Vault Sync v0.3

A portable, incremental archive and isolated recovery tool plus AI Skill for common coding agents.

It separates three responsibilities:

- **Adapter modules** understand where one application stores transcripts, SQLite state, indexes, sensitive files, and optional native restore capabilities.
- **The core synchronizer** handles folder creation, incremental copy, hashing, conflicts, SQLite snapshots, reports, and verification.
- **The restore engine** creates a new isolated native application home without modifying the active installation or archive.

## What changed in v0.3

- Added verified adapters for Gemini CLI, Qwen Code, Kimi Code CLI, OpenCode, Goose, Hermes Agent, and Aider.
- Added exact include/exclude patterns so adapters do not treat every JSON file as a conversation.
- Added support for multi-file sessions such as Kimi `context.jsonl`, `wire.jsonl`, and `state.json`.
- Added SQLite-only adapters for applications that store all messages in one shared database.
- Added upstream-source research and explicit support boundaries in `references/common-adapters.md`.
- Added isolated Codex single-session and full-library restore without overwriting the active `.codex` directory.
- Added GitHub Actions tests on Python 3.10 and 3.12.

## Supported adapters

```bash
python scripts/vault_sync.py --mode list-apps
```

### Transcript or session-artifact adapters

- `codex`
- `claude-code` (`claude` alias)
- `gemini-cli` (`gemini` alias)
- `qwen-code` (`qwen` alias)
- `kimi-cli` (`kimi` alias)

These support incremental file-level copy, duplicate detection, growing-session updates, and conflict preservation.

### SQLite snapshot adapters

- `opencode`
- `goose`
- `hermes-agent` (`hermes` alias)

These applications store full session history in a shared SQLite database. The vault saves a consistent database snapshot and verifies it with `PRAGMA quick_check`; it does not merge databases or delete individual rows.

### Project history adapter

- `aider`

Aider writes rolling history files in a project root rather than one file per session. Use `--source-root` to select the repository when the command is not run inside that project.

See [common adapter research](references/common-adapters.md) for paths, evidence, exclusions, and limitations.

## Basic archive workflow

Inspect an application's storage:

```bash
python scripts/vault_sync.py --app codex --mode inspect
```

Preview the exact destination folder:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode layout \
  --vault-root /path/to/AgentSessionVault \
  --machine-id leon-main-pc
```

First run as a dry run:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode sync \
  --vault-root /path/to/AgentSessionVault \
  --machine-id leon-main-pc \
  --dry-run
```

Synchronize and verify:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode sync \
  --vault-root /path/to/AgentSessionVault \
  --machine-id leon-main-pc

python scripts/vault_sync.py \
  --app codex \
  --mode verify \
  --vault-root /path/to/AgentSessionVault \
  --machine-id leon-main-pc
```

Windows PowerShell example:

```powershell
python .\scripts\vault_sync.py `
  --app gemini-cli `
  --mode sync `
  --vault-root "E:\AgentSessionVault" `
  --machine-id "leon-windows-main"
```

## Codex isolated restore

Codex currently supports native recovery into a **new directory**. The tool never restores directly into the active `%USERPROFILE%\.codex` or `~/.codex` directory.

Single-session dry run:

```powershell
python .\scripts\vault_sync.py `
  --app codex `
  --mode restore `
  --restore-scope session `
  --session-id "<thread-uuid>" `
  --vault-root "E:\AgentSessionVault" `
  --machine-id "leon-windows-main" `
  --restore-root "E:\Codex-Recovery-Single" `
  --dry-run
```

Remove `--dry-run` to publish the recovery directory.

Full isolated restore:

```powershell
python .\scripts\vault_sync.py `
  --app codex `
  --mode restore `
  --restore-scope full `
  --vault-root "E:\AgentSessionVault" `
  --machine-id "leon-windows-main" `
  --restore-root "E:\Codex-Recovery-All"
```

Restore behavior:

- verifies archived file hashes before writing;
- requires a restore path that does not already exist;
- writes through a temporary staging directory and publishes by atomic rename;
- restores rollout JSONL files and relevant indexes;
- does **not** activate an old state SQLite snapshot;
- lets Codex create a fresh state database and backfill it from restored rollouts;
- activates an individually restored archived session so it can be resumed;
- generates Windows and POSIX launch scripts plus `restore-report.json`.

See [Codex isolated restore](references/codex-restore.md) for the design rationale and safety rules.

## Folder rules

```text
AgentSessionVault/
├── vault.json
└── apps/
    └── <app_id>/
        └── machines/
            └── <machine_id>/
                ├── machine.json
                ├── manifest.json
                ├── native/
                ├── metadata/
                ├── conflicts/
                └── reports/
```

The user chooses only the vault root. The adapter supplies `app_id`, precise session collections, SQLite/index patterns, credential exclusions, and optional restore strategy. The machine folder comes from `--machine-id`, `AGENT_VAULT_MACHINE_ID`, or a deterministic host-derived fallback.

## Add another application

Create one module under:

```text
scripts/session_vault/adapters/<app_id>.py
```

Use `@register_adapter(...)` and return an `AdapterSpec`. The registry imports new adapter modules automatically. Define precise `include_patterns` instead of scanning every JSON file. Native restore must remain disabled unless an evidence-backed restore strategy and tests exist. See:

- `references/adapter-contract.md`
- `references/common-adapters.md`
- `references/codex-restore.md`
- existing adapter modules and tests

## Tests

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
```

The tool never modifies source application files and excludes authentication files by default.
