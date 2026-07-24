from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "vault_sync.py"


class VerifySidecarFailureTests(unittest.TestCase):
    def test_integrity_errors_emit_failed_terminal_event(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            machine_root = vault / "apps" / "codex" / "machines" / "test-machine"
            session_path = machine_root / "native" / "sessions" / "session.jsonl"
            session_path.parent.mkdir(parents=True)
            session_path.write_text("tampered", encoding="utf-8")
            (vault / "vault.json").write_text(
                json.dumps({"type": "agent-session-vault", "schema_version": 2}),
                encoding="utf-8",
            )
            (machine_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "layout_version": 1,
                        "app_id": "codex",
                        "machine_id": "test-machine",
                        "sessions": {
                            "codex:test-machine:session": {
                                "vault_path": "native/sessions/session.jsonl",
                                "sha256": "0" * 64,
                            }
                        },
                        "metadata": {},
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ENTRYPOINT),
                    "--mode",
                    "verify",
                    "--app",
                    "codex",
                    "--source-root",
                    str(root / "unused-source"),
                    "--vault-root",
                    str(vault),
                    "--machine-id",
                    "test-machine",
                    "--output-format",
                    "jsonl",
                    "--request-id",
                    "verify-failure",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 3, result.stderr)
            events = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(events[0]["event"], "started")
            self.assertTrue(any(event["event"] == "progress" for event in events))
            self.assertEqual(events[-1]["event"], "failed")
            self.assertEqual(events[-1]["error"]["code"], "VERIFY_FAILED")
            report = events[-1]["error"]["details"]["report"]
            self.assertFalse(report["ok"])
            self.assertEqual(report["errors"], 1)
            self.assertIn("hash mismatch", report["details"][0])

    def test_pretty_cli_keeps_existing_verify_result_contract(self):
        # The behavior change is Sidecar-only. Legacy pretty mode still reports
        # the verification object and exits successfully for compatibility.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            machine_root = vault / "apps" / "codex" / "machines" / "test-machine"
            machine_root.mkdir(parents=True)
            (machine_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "layout_version": 1,
                        "app_id": "codex",
                        "machine_id": "test-machine",
                        "sessions": {},
                        "metadata": {},
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ENTRYPOINT),
                    "--mode",
                    "verify",
                    "--app",
                    "codex",
                    "--source-root",
                    str(root / "unused-source"),
                    "--vault-root",
                    str(vault),
                    "--machine-id",
                    "test-machine",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
