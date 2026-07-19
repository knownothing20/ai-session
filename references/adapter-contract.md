# Adapter Contract

Each supported application needs an adapter that defines:

1. `app_id`: stable lowercase identifier, such as `codex`.
2. Native source-root detection rules.
3. Session roots and session file patterns.
4. How to extract a stable native session/thread ID.
5. SQLite state files that require a consistent snapshot.
6. Index files that should be copied atomically.
7. Files that must be excluded, especially authentication and secrets.

## Safety requirements

- Source storage is always read-only.
- Never merge or edit a vendor SQLite database.
- Save the latest consistent database snapshot per app and per source machine.
- Do not treat title, filename timestamp, project path, or file modification time as a unique session identity.
- Before activating a new adapter, run inspect mode and verify it against real local files.

## Duplicate identity

Logical identity:

`app_id + machine_id + native_session_id`

Content identity:

`SHA-256(file bytes)`

Rules:

- Same logical identity and same hash: skip.
- Same logical identity and destination is a byte prefix of source: active session grew; atomically update it.
- Same logical identity but divergent content: preserve old revision under `conflicts/`, then update current copy.
- Different logical identity but same hash: keep both native paths for restore safety and mark them as duplicate content.
