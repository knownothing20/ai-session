# Agent Session Vault Sync v0.1

A portable Skill design and deterministic helper script for incrementally archiving local AI coding-agent sessions to a user-selected disk.

## Included adapters

- Codex: transcript JSONL, archived transcripts, `state_*.sqlite`, `session_index.jsonl`.
- Claude Code: project transcript JSONL and optional `history.jsonl`.

## Basic commands

```bash
python scripts/vault_sync.py --app codex --mode inspect
python scripts/vault_sync.py --app codex --mode sync --vault-root /path/to/AgentSessionVault --dry-run
python scripts/vault_sync.py --app codex --mode sync --vault-root /path/to/AgentSessionVault
python scripts/vault_sync.py --app codex --mode verify --vault-root /path/to/AgentSessionVault
```

Windows example:

```powershell
python .\scripts\vault_sync.py --app codex --mode sync --vault-root "E:\AgentSessionVault" --dry-run
```

The tool never modifies the source application's files. Authentication files are not copied.
