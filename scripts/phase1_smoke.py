#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "vault_sync.py"
PROTOCOL = "ai-session-vault-sidecar"


class SmokeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def run_sidecar(*args: str, expect_progress: bool = True) -> dict[str, Any]:
    request_id = uuid.uuid4().hex
    result = subprocess.run(
        [
            sys.executable,
            str(ENTRYPOINT),
            *args,
            "--output-format",
            "jsonl",
            "--request-id",
            request_id,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise SmokeFailure(
            f"Sidecar returned invalid JSONL for {args}: {exc}\nstdout={result.stdout}\nstderr={result.stderr}"
        ) from exc

    require(events, f"Sidecar returned no events for {args}: {result.stderr}")
    require(events[0]["event"] == "started", f"First event is not started: {events}")
    require(
        events[-1]["event"] in {"completed", "failed"},
        f"Last event is not terminal: {events[-1]}",
    )
    require(
        [event["sequence"] for event in events] == list(range(1, len(events) + 1)),
        f"Sequences are not monotonic: {events}",
    )
    for event in events:
        require(event["protocol"] == PROTOCOL, f"Unexpected protocol: {event}")
        require(event["protocol_version"] == 1, f"Unexpected protocol version: {event}")
        require(event["request_id"] == request_id, f"Request ID mismatch: {event}")
    if expect_progress:
        require(
            any(event["event"] == "progress" for event in events),
            f"No progress event was emitted for {args}",
        )
    if result.returncode != 0 or events[-1]["event"] == "failed":
        raise SmokeFailure(
            f"Sidecar failed for {args}: returncode={result.returncode}, "
            f"event={events[-1]}, stderr={result.stderr}"
        )
    return {
        "events": events,
        "data": events[-1].get("data", {}),
        "stderr": result.stderr,
    }


def write_rollout(path: Path, session_id: str, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "session_meta", "id": session_id})
        + "\n"
        + json.dumps({"type": "message", "text": text})
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-session-phase1-") as temp:
        root = Path(temp)
        source = root / "codex-home"
        vault = root / "vault"
        machine_id = "phase1-smoke-machine"
        active_id = str(uuid.uuid4())
        archived_id = str(uuid.uuid4())

        write_rollout(
            source
            / "sessions"
            / "2026"
            / "07"
            / "24"
            / f"rollout-2026-07-24T00-00-00-{active_id}.jsonl",
            active_id,
            "active smoke session",
        )
        write_rollout(
            source
            / "archived_sessions"
            / f"rollout-2026-07-23T00-00-00-{archived_id}.jsonl",
            archived_id,
            "archived smoke session",
        )
        (source / "session_index.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"id": active_id, "thread_name": "active"}),
                    json.dumps({"id": archived_id, "thread_name": "archived"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        with closing(sqlite3.connect(source / "state_5.sqlite")) as database:
            database.execute("CREATE TABLE threads(id TEXT PRIMARY KEY, title TEXT)")
            database.executemany(
                "INSERT INTO threads VALUES (?, ?)",
                [(active_id, "active"), (archived_id, "archived")],
            )
            database.commit()

        discovered = run_sidecar("--mode", "list-apps")
        adapter_ids = {
            adapter["app_id"] for adapter in discovered["data"].get("adapters", [])
        }
        require("codex" in adapter_ids, "Codex adapter was not discovered")

        inspected = run_sidecar(
            "--mode",
            "inspect",
            "--app",
            "codex",
            "--source-root",
            str(source),
            "--vault-root",
            str(vault),
            "--machine-id",
            machine_id,
        )
        require(inspected["data"].get("session_files") == 2, "Inspect did not find two sessions")

        run_sidecar(
            "--mode",
            "sync",
            "--app",
            "codex",
            "--source-root",
            str(source),
            "--vault-root",
            str(vault),
            "--machine-id",
            machine_id,
            "--dry-run",
        )
        require(not vault.exists(), "Backup dry-run created the Vault directory")

        synced = run_sidecar(
            "--mode",
            "sync",
            "--app",
            "codex",
            "--source-root",
            str(source),
            "--vault-root",
            str(vault),
            "--machine-id",
            machine_id,
        )
        require(synced["data"].get("sessions_copied") == 2, "Real backup did not copy two sessions")
        require(Path(synced["data"]["report_path"]).is_file(), "Sync report was not written")

        verified = run_sidecar(
            "--mode",
            "verify",
            "--app",
            "codex",
            "--source-root",
            str(source),
            "--vault-root",
            str(vault),
            "--machine-id",
            machine_id,
        )
        require(verified["data"].get("ok") is True, f"Vault verification failed: {verified}")

        session_restore = root / "recovery-session"
        run_sidecar(
            "--mode",
            "restore",
            "--app",
            "codex",
            "--source-root",
            str(source),
            "--vault-root",
            str(vault),
            "--machine-id",
            machine_id,
            "--restore-root",
            str(session_restore),
            "--restore-scope",
            "session",
            "--session-id",
            archived_id,
            "--dry-run",
        )
        require(not session_restore.exists(), "Restore dry-run created an output directory")

        restored_session = run_sidecar(
            "--mode",
            "restore",
            "--app",
            "codex",
            "--source-root",
            str(source),
            "--vault-root",
            str(vault),
            "--machine-id",
            machine_id,
            "--restore-root",
            str(session_restore),
            "--restore-scope",
            "session",
            "--session-id",
            archived_id,
        )
        require(restored_session["data"].get("sessions_restored") == 1, "Single restore count is wrong")
        require(len(list((session_restore / "sessions").rglob("*.jsonl"))) == 1, "Archived session was not activated")
        require(not list(session_restore.glob("*.sqlite")), "Old SQLite database was restored")

        full_restore = root / "recovery-full"
        restored_full = run_sidecar(
            "--mode",
            "restore",
            "--app",
            "codex",
            "--source-root",
            str(source),
            "--vault-root",
            str(vault),
            "--machine-id",
            machine_id,
            "--restore-root",
            str(full_restore),
            "--restore-scope",
            "full",
        )
        require(restored_full["data"].get("sessions_restored") == 2, "Full restore count is wrong")
        require((full_restore / "restore-report.json").is_file(), "Restore report is missing")
        require(not list(full_restore.glob("*.sqlite")), "Full restore published old SQLite")

        summary = {
            "ok": True,
            "adapter_count": len(adapter_ids),
            "sessions_backed_up": synced["data"].get("sessions_copied"),
            "sessions_verified": verified["data"].get("sessions_checked"),
            "single_restore": restored_session["data"].get("sessions_restored"),
            "full_restore": restored_full["data"].get("sessions_restored"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        print(f"Phase 1 smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
