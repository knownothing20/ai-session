from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from session_vault.utils import SyncError, VaultLock  # noqa: E402


class VaultLockTests(unittest.TestCase):
    def test_reclaims_recent_lock_from_dead_process(self):
        with tempfile.TemporaryDirectory() as temp:
            lock_path = Path(temp) / ".sync.lock"
            lock_path.write_text(
                json.dumps({"pid": 2_147_483_647, "created_at": "2026-01-01T00:00:00Z"}),
                encoding="utf-8",
            )

            with VaultLock(lock_path, False):
                self.assertTrue(lock_path.exists())
            self.assertFalse(lock_path.exists())

    def test_rejects_lock_owned_by_current_process(self):
        with tempfile.TemporaryDirectory() as temp:
            lock_path = Path(temp) / ".sync.lock"
            with VaultLock(lock_path, False):
                with self.assertRaises(SyncError):
                    with VaultLock(lock_path, False):
                        pass


if __name__ == "__main__":
    unittest.main()
