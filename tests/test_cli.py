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
        self.assertEqual(
            {item["app_id"] for item in data["adapters"]},
            {"codex", "claude-code"},
        )


if __name__ == "__main__":
    unittest.main()
