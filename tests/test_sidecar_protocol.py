from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.session_vault.protocol import (
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    SidecarEmitter,
)

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "vault_sync.py"


class SidecarEmitterTests(unittest.TestCase):
    def test_emits_ordered_lifecycle_events(self):
        stream = io.StringIO()
        emitter = SidecarEmitter(
            "sync",
            request_id="request-123",
            stream=stream,
        )

        emitter.started({"dry_run": True})
        emitter.progress({"phase": "scan", "current": 1, "total": 2})
        emitter.completed({"ok": True})

        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual([item["sequence"] for item in events], [1, 2, 3])
        self.assertEqual([item["event"] for item in events], ["started", "progress", "completed"])
        for event in events:
            self.assertEqual(event["protocol"], PROTOCOL_NAME)
            self.assertEqual(event["protocol_version"], PROTOCOL_VERSION)
            self.assertEqual(event["request_id"], "request-123")
            self.assertEqual(event["operation"], "sync")

    def test_failed_event_has_structured_error(self):
        stream = io.StringIO()
        emitter = SidecarEmitter("verify", stream=stream)
        event = emitter.failed(
            "SYNC_ERROR",
            "manifest missing",
            retryable=False,
            details={"path": "X:/vault/manifest.json"},
        )

        self.assertEqual(event["event"], "failed")
        self.assertEqual(event["error"]["code"], "SYNC_ERROR")
        self.assertFalse(event["error"]["retryable"])
        self.assertEqual(event["error"]["details"]["path"], "X:/vault/manifest.json")


class SidecarCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ENTRYPOINT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_list_apps_jsonl_has_started_and_completed(self):
        result = self.run_cli(
            "--mode",
            "list-apps",
            "--output-format",
            "jsonl",
            "--request-id",
            "desktop-request",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([item["event"] for item in events], ["started", "completed"])
        self.assertEqual(events[0]["request_id"], "desktop-request")
        adapters = {item["app_id"] for item in events[1]["data"]["adapters"]}
        self.assertIn("codex", adapters)
        self.assertIn("claude-code", adapters)

    def test_validation_failure_is_emitted_on_stdout(self):
        result = self.run_cli(
            "--app",
            "codex",
            "--mode",
            "restore",
            "--vault-root",
            str(ROOT / "missing-vault"),
            "--machine-id",
            "test-machine",
            "--output-format",
            "jsonl",
            "--request-id",
            "restore-request",
        )

        self.assertEqual(result.returncode, 2)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([item["event"] for item in events], ["started", "failed"])
        self.assertEqual(events[-1]["request_id"], "restore-request")
        self.assertEqual(events[-1]["error"]["code"], "SYNC_ERROR")
        self.assertIn("--restore-root is required", events[-1]["error"]["message"])

    def test_default_pretty_output_remains_compatible(self):
        result = self.run_cli("--mode", "list-apps")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("adapters", data)
        self.assertNotIn("protocol", data)


if __name__ == "__main__":
    unittest.main()
