# Common application adapter research

This document records the evidence and support boundary for each adapter. Paths and formats are based on upstream source code, not guessed from third-party blog posts.

## Support levels

- **Transcript files**: one session, or a stable set of files belonging to one session, can be incrementally copied and deduplicated.
- **SQLite snapshot**: full session data is stored in a shared database. The vault saves a consistent database snapshot; it does not merge or delete individual sessions inside the vendor database.
- **Project history**: the application writes one rolling history file per project rather than one file per session.
- **Native restore**: an adapter has a separately tested strategy for constructing a usable isolated application home. Archive support alone does not imply restore support.

## Implemented adapters

| App ID | Application | Storage type | Native storage | Stable identity | Important exclusions / boundary |
|---|---|---|---|---|---|
| `codex` | OpenAI Codex | Transcript files + SQLite/index + isolated restore | `CODEX_HOME` or `~/.codex`; `sessions/**/*.jsonl`, `archived_sessions/**/*.jsonl`, `state_*.sqlite`, `session_index.jsonl` | Native session UUID from rollout metadata or filename | Excludes `auth.json` and diagnostic log DBs. Restore publishes rollouts/indexes into a new `CODEX_HOME`, skips old state SQLite, and lets Codex backfill a fresh DB |
| `claude-code` | Claude Code | Transcript files | `~/.claude/projects/**/*.jsonl` | Native session ID from transcript | Credentials and configuration are not included; native restore is not declared |
| `gemini-cli` | Google Gemini CLI | Transcript files + project index | `~/.gemini/tmp/<project>/chats/session-*.json[l]`; `~/.gemini/projects.json` | Full `sessionId` from the first metadata record | Excludes OAuth, MCP OAuth, A2A OAuth and account files; native restore is not declared |
| `qwen-code` | Qwen Code | Transcript files | `QWEN_RUNTIME_DIR` / `QWEN_HOME` / `~/.qwen`; `projects/*/chats/*.jsonl` and archived chat files; legacy `tmp/*/chats` | Session UUID plus active/archive state | Runtime and worktree sidecar JSON files are intentionally not treated as transcripts; native restore is not declared |
| `kimi-cli` | Kimi Code CLI | Multi-file session artifacts + index | `KIMI_SHARE_DIR` or `~/.kimi`; `sessions/<workdir>/<session>/context.jsonl`, `wire.jsonl`, `state.json`; legacy JSONL; `kimi.json` | Session directory UUID plus artifact path | Context, wire events and state are preserved as separate artifacts; native restore is not declared |
| `opencode` | OpenCode | SQLite snapshot | XDG data directory `opencode/opencode.db`, channel DB, or `OPENCODE_DB` | Database-level snapshot | No per-session deletion, merge or native restore in the vault |
| `goose` | Goose | SQLite snapshot | Goose data dir `sessions/sessions.db`; `GOOSE_PATH_ROOT/data` when overridden | Database-level snapshot | Default platform path is existence-detected; use `goose info` or `--source-root` when not found; native restore is not declared |
| `hermes-agent` | Hermes Agent | SQLite snapshot with FTS | `HERMES_HOME/state.db` or `~/.hermes/state.db` | Database-level snapshot | The DB contains full messages and search indexes; credential files are not copied; native restore is not declared |
| `aider` | Aider | Project rolling history | Project root `.aider.chat.history.md`, `.aider.input.history`, optional `.aider.llm.history` | History filename | This is not one-file-per-session. Custom CLI history paths require `--source-root`; native restore is not declared |

## Upstream evidence

### Codex

- Rollout-to-state backfill and active/archive scanning: <https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/rollout/src/state_db_tests.rs>
- Doctor recommendation to rebuild a missing state DB from rollout files: <https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/cli/src/doctor/thread_inventory.rs>
- Resume by thread ID: <https://github.com/openai/codex/blob/44d76c6a6dd04fa2efc302b906ac8774267a1272/codex-rs/utils/cli/src/resume_command.rs>

### Gemini CLI

- Global and project temp storage: <https://github.com/google-gemini/gemini-cli/blob/acae7124bdd849e554eaa5e090199a0cf08cd782/packages/core/src/config/storage.ts>
- Session record schema and `sessionId`: <https://github.com/google-gemini/gemini-cli/blob/acae7124bdd849e554eaa5e090199a0cf08cd782/packages/core/src/services/chatRecordingTypes.ts>
- JSON/JSONL recording and resume loader: <https://github.com/google-gemini/gemini-cli/blob/acae7124bdd849e554eaa5e090199a0cf08cd782/packages/core/src/services/chatRecordingService.ts>

### Qwen Code

- Runtime root, `QWEN_HOME`, `QWEN_RUNTIME_DIR`, projects and temp paths: <https://github.com/QwenLM/qwen-code/blob/0c271659df374568ae118282a0af05c5ef0124bd/packages/core/src/config/storage.ts>
- Active/archive chat paths and JSONL session format: <https://github.com/QwenLM/qwen-code/blob/0c271659df374568ae118282a0af05c5ef0124bd/packages/core/src/services/sessionService.ts>

### Kimi Code CLI

- `KIMI_SHARE_DIR` and `~/.kimi`: <https://github.com/MoonshotAI/kimi-cli/blob/4a550effdfcb29a25a5d325bf935296cc50cd417/src/kimi_cli/share.py>
- Work-directory index and session directory calculation: <https://github.com/MoonshotAI/kimi-cli/blob/4a550effdfcb29a25a5d325bf935296cc50cd417/src/kimi_cli/metadata.py>
- Current and legacy session discovery: <https://github.com/MoonshotAI/kimi-cli/blob/4a550effdfcb29a25a5d325bf935296cc50cd417/src/kimi_cli/web/store/sessions.py>
- Session state filename and fields: <https://github.com/MoonshotAI/kimi-cli/blob/4a550effdfcb29a25a5d325bf935296cc50cd417/src/kimi_cli/session_state.py>

### OpenCode

- XDG-backed data directory: <https://github.com/anomalyco/opencode/blob/7985c2066a8f38c48a7d8fefbafcbab96ffa3117/packages/core/src/global.ts>
- Database filename, `OPENCODE_DB` and channel-specific DBs: <https://github.com/anomalyco/opencode/blob/7985c2066a8f38c48a7d8fefbafcbab96ffa3117/packages/core/src/database/database.ts>
- SQLite WAL behavior: <https://github.com/anomalyco/opencode/blob/7985c2066a8f38c48a7d8fefbafcbab96ffa3117/packages/core/src/database/sqlite.bun.ts>

### Goose

- Session DB name and storage root: <https://github.com/aaif-goose/goose/blob/8e78960e535ab7f34630e7c5921a42f146cbc9f4/crates/goose/src/session/session_manager.rs>
- Platform paths and `GOOSE_PATH_ROOT`: <https://github.com/aaif-goose/goose/blob/8e78960e535ab7f34630e7c5921a42f146cbc9f4/crates/goose/src/config/paths.rs>
- `goose info` prints the exact session DB path: <https://github.com/aaif-goose/goose/blob/8e78960e535ab7f34630e7c5921a42f146cbc9f4/crates/goose-cli/src/commands/info.rs>

### Hermes Agent

- SQLite session architecture and FTS schema: <https://github.com/NousResearch/hermes-agent/blob/26480e6c57c3558442a73c2dffe313996b19417f/website/docs/developer-guide/session-storage.md>
- Official backup uses the SQLite backup API and excludes WAL sidecars: <https://github.com/NousResearch/hermes-agent/blob/26480e6c57c3558442a73c2dffe313996b19417f/hermes_cli/backup.py>

### Aider

- Default input and chat history filenames and configurable LLM history: <https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/aider/args.py>

## Deferred adapters

The following are deliberately not implemented yet:

- Cursor, Windsurf, Trae, WorkBuddy and QClaw: no stable, public, vendor-documented session storage contract was found. Their Electron/IDE databases can change between versions and may contain credentials or unrelated application state.
- Cline, Roo Code and Continue: open source, but storage is tied to VS Code-compatible extension hosts, profiles, remote SSH/WSL contexts and editor-specific global storage roots. They need a host-aware discovery layer rather than one hard-coded path.
- OpenClaw: the name currently refers to multiple projects and distributions. An adapter needs the exact repository/build and a sample storage inventory before activation.

For a deferred application, run a read-only inventory and add an adapter only after confirming its native session ID, transcript files or DB, indexes, credential exclusions, and any proposed restore semantics.
