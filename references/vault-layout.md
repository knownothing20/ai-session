# Vault Folder Rules

The portable vault root is selected by the user. The tool never guesses a drive letter.

```text
<vault-root>/
├── vault.json
└── apps/
    └── <app_id>/
        └── machines/
            └── <machine_id>/
                ├── machine.json
                ├── manifest.json
                ├── native/
                │   └── <collection>/...
                ├── metadata/
                │   ├── latest/
                │   └── history/<timestamp>/
                ├── conflicts/<session_id>/
                └── reports/
```

## Naming rules

- `app_id` comes from the adapter and must stay stable after release.
- `machine_id` priority: `--machine-id` → `AGENT_VAULT_MACHINE_ID` → deterministic host-derived ID.
- `<collection>` comes from the adapter, for example `sessions`, `archived_sessions`, or `projects`.
- Source-relative transcript paths are preserved below each collection.
- Database and index snapshots are isolated per application and per machine.

## Safety rules

- A non-empty directory without `vault.json` is never initialized automatically.
- Source deletions do not delete archive copies.
- A changed SQLite file creates a consistent latest snapshot; the previous snapshot moves to history.
- A divergent transcript with the same native ID preserves the old revision in `conflicts/`.
