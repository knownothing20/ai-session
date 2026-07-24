# AI Session Vault

A local-first desktop application and portable Vault Core for browsing, backing up, verifying, and safely restoring AI coding sessions.

The repository is a monorepo:

```text
ai-session/
├── desktop/                  Tauri / React / Rust desktop application
├── scripts/session_vault/    Python Vault Core
├── tests/
├── docs/
└── references/
```

The desktop base is derived from the MIT-licensed `jhlee0409/claude-code-history-viewer` v1.22.0. The Python Vault Core remains the only implementation of reliable backup, integrity verification, conflict preservation, SQLite snapshots, and native restore.

## Development status

The project uses five large stages.

```text
Stage 0: Open-source desktop baseline import          completed
Stage 1: Backup, verification and Codex restore UI    online implementation complete; Windows acceptance pending
Stage 2: Doctor, repair and session management        not started
Stage 3: Handoff, export and Vault search             not started
Stage 4: Usage, AI analysis and productization        not started
```

Stage 1 currently provides an experimental **Session Vault** console under:

```text
Settings → Session Vault
```

Implemented online:

- supported-application discovery;
- Vault folder, machine ID, and optional source override;
- source inspection and Vault-layout preview;
- incremental backup dry-run and real backup;
- hash and SQLite integrity verification;
- Codex single-session/full-library restore dry-run;
- Codex single-session/full-library isolated restore;
- real-time JSONL progress, cancellation, timeout, reports, and structured errors;
- English, Korean, Japanese, Simplified Chinese, and Traditional Chinese UI.

This code is not considered Stage 1 complete until the Windows validation and manual UI matrix pass. Run from `D:\GitHub\ai-session`:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

The script requires explicit `YES` confirmation after the complete desktop workflow and writes `docs/PHASE_1_LOCAL_VALIDATION.json`.

## Architecture

The project separates responsibilities:

- **CCHV-derived Provider layer** reads and renders native sessions for viewing, search, and statistics.
- **Adapter modules** define exact native transcript, SQLite, index, exclusion, and optional restore rules.
- **Vault Core** handles folder creation, incremental copy, hashing, conflicts, SQLite snapshots, reports, verification, locking, and restore.
- **Rust Sidecar bridge** launches the Vault Core without a shell, validates JSONL events, manages cancellation and timeout, and emits Tauri events.
- **React Vault console** configures operations and displays progress, results, warnings, and recovery reports.

Stage 1 uses a controlled system Python runtime. The defaults may be overridden with:

```text
AI_SESSION_VAULT_PYTHON=<python executable>
AI_SESSION_VAULT_SIDECAR=<script or executable>
```

A signed, no-Python executable Sidecar and installer integration belong to Stage 4 productization.

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

These applications store full session history in a shared SQLite database. The Vault saves a consistent database snapshot and verifies it with `PRAGMA quick_check`; it does not merge databases or delete individual rows.

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

Codex supports native recovery into a **new directory**. The tool never restores directly into the active `%USERPROFILE%\.codex` or `~/.codex` directory.

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

The user chooses only the Vault root. The adapter supplies `app_id`, precise session collections, SQLite/index patterns, credential exclusions, and optional restore strategy. The machine folder comes from `--machine-id`, `AGENT_VAULT_MACHINE_ID`, or a deterministic host-derived fallback.

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

## Documentation

- [Full product plan](docs/FULL_DEVELOPMENT_PLAN.md)
- [Development stage status](docs/DEVELOPMENT_STAGE_STATUS.md)
- [Stage 1 implementation](docs/PHASE_1_BACKUP_RESTORE_INTEGRATION.md)
- [Sidecar Protocol v1](docs/SIDECAR_PROTOCOL_V1.md)
- [Stage 1 runtime strategy](docs/PHASE_1_RUNTIME_STRATEGY.md)
- [Stage 1 acceptance report](docs/PHASE_1_ACCEPTANCE_REPORT.md)

## Tests

Run Python tests manually:

```bash
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
python scripts/phase1_smoke.py
```

Run the complete Windows Stage 1 validation:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\validate_phase1.ps1 `
  -Launch
```

No GitHub Actions workflow is installed or permitted on the development branch. The tool treats source application storage as read-only and excludes authentication files, OAuth data, logs, and caches by default.
