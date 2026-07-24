from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_list_apps(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/vault_sync.py"), "--mode", "list-apps"],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        adapters = {item["app_id"]: item for item in data["adapters"]}
        self.assertEqual(
            set(adapters),
            {
                "aider",
                "claude-code",
                "codex",
                "gemini-cli",
                "goose",
                "hermes-agent",
                "kimi-cli",
                "opencode",
                "qwen-code",
            },
        )
        self.assertEqual(
            adapters["codex"]["restore_strategy"], "codex-rollout-backfill"
        )
        self.assertIsNone(adapters["claude-code"]["restore_strategy"])

    def test_restore_requires_destination(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/vault_sync.py"),
                "--app",
                "codex",
                "--mode",
                "restore",
                "--vault-root",
                str(ROOT / "missing-vault"),
                "--machine-id",
                "test-machine",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--restore-root is required", result.stderr)


if __name__ == "__main__":
    unittest.main()
