# Agent Session Vault Sync v0.2

A portable, incremental archive tool and AI Skill for Codex, Claude Code, and future coding agents.

It separates two responsibilities:

- **Adapter modules** understand where one application stores transcripts, SQLite state, indexes, and sensitive files.
- **The core synchronizer** handles folder creation, incremental copy, hashing, conflicts, SQLite snapshots, reports, and verification.

## What changed in v0.2

- Codex and Claude Code adapters are independent modules.
- New adapters are discovered automatically from `scripts/session_vault/adapters/`.
- No central `if/elif` adapter switch.
- Stable folder rules documented in `references/vault-layout.md`.
- New `--machine-id`, `layout`, and `list-apps` commands.
- Manifest v1 archives remain readable and upgrade to schema v2 on the next real sync.
- Verification now checks transcripts, metadata hashes, and SQLite integrity.
- Added standard-library `unittest` coverage for repeat sync, append, duplicate, conflict, SQLite, and folder layout.

## Supported adapters

```bash
python scripts/vault_sync.py --mode list-apps
```

Currently:

- `codex`
- `claude-code` (`claude` alias)

## Basic workflow

Inspect local Codex storage:

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

Synchronize:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode sync \
  --vault-root /path/to/AgentSessionVault \
  --machine-id leon-main-pc
```

Verify:

```bash
python scripts/vault_sync.py \
  --app codex \
  --mode verify \
  --vault-root /path/to/AgentSessionVault \
  --machine-id leon-main-pc
```

Windows PowerShell example:

```powershell
python .\scripts\vault_sync.py `
  --app codex `
  --mode sync `
  --vault-root "E:\AgentSessionVault" `
  --machine-id "leon-windows-main"
```

## Folder rules

```text
AgentSessionVault/
├── vault.json
└── apps/
    └── codex/
        └── machines/
            └── leon-windows-main/
                ├── machine.json
                ├── manifest.json
                ├── native/
                ├── metadata/
                ├── conflicts/
                └── reports/
```

The user chooses only the vault root. The adapter supplies `app_id` and collection names. The machine folder comes from `--machine-id`, `AGENT_VAULT_MACHINE_ID`, or a deterministic host-derived fallback.

## Add another application

Create one module under:

```text
scripts/session_vault/adapters/<app_id>.py
```

Use `@register_adapter(...)` and return an `AdapterSpec`. The registry imports new adapter modules automatically. See `references/adapter-contract.md`.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tool never modifies source application files and excludes authentication files by default.
