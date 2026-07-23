from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from session_vault.models import AdapterSpec, SessionCollection  # noqa: E402
from session_vault.restore import restore_archive  # noqa: E402
from session_vault.utils import SyncError, hash_file  # noqa: E402


class CodexRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.machine_root = base / "vault/apps/codex/machines/test-machine"
        self.machine_root.mkdir(parents=True)
        self.source_root = base / "active-codex"
        self.restore_root = base / "codex-recovery"
        self.spec = AdapterSpec(
            app_id="codex",
            display_name="OpenAI Codex",
            aliases=("codex",),
            source_root=self.source_root,
            collections=(
                SessionCollection("sessions", self.source_root / "sessions"),
                SessionCollection(
                    "archived_sessions", self.source_root / "archived_sessions"
                ),
            ),
            restore_strategy="codex-rollout-backfill",
        )
        self.session_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        sessions: dict[str, dict] = {}
        for index, session_id in enumerate(self.session_ids):
            relative = (
                Path("native/sessions/2026/07/20")
                / f"rollout-2026-07-20T00-00-0{index}-{session_id}.jsonl"
            )
            path = self.machine_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"type": "session_meta", "id": session_id}) + "\n",
                encoding="utf-8",
            )
            sessions[f"codex:test-machine:{session_id}"] = {
                "native_session_id": session_id,
                "source_collection": "sessions",
                "vault_path": str(relative),
                "sha256": hash_file(path),
            }

        index_path = self.machine_root / "metadata/latest/session_index.jsonl"
        index_path.parent.mkdir(parents=True)
        index_path.write_text(
            "\n".join(
                json.dumps({"id": session_id, "thread_name": f"thread-{index}"})
                for index, session_id in enumerate(self.session_ids)
            )
            + "\n",
            encoding="utf-8",
        )
        database_path = self.machine_root / "metadata/latest/state_5.sqlite"
        with sqlite3.connect(database_path) as database:
            database.execute("CREATE TABLE threads(id TEXT PRIMARY KEY)")
            database.commit()

        manifest = {
            "schema_version": 2,
            "layout_version": 1,
            "app_id": "codex",
            "machine_id": "test-machine",
            "sessions": sessions,
            "metadata": {
                "session_index.jsonl": {
                    "kind": "index",
                    "snapshot_path": "metadata/latest/session_index.jsonl",
                    "snapshot_sha256": hash_file(index_path),
                },
                "state_5.sqlite": {
                    "kind": "sqlite",
                    "snapshot_path": "metadata/latest/state_5.sqlite",
                    "snapshot_sha256": hash_file(database_path),
                },
            },
        }
        (self.machine_root / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_single_restore_is_isolated_and_rebuildable(self):
        report = restore_archive(
            self.spec,
            self.machine_root,
            self.restore_root,
            "session",
            self.session_ids[0],
        )
        self.assertEqual(report["sessions_restored"], 1)
        self.assertEqual(len(list((self.restore_root / "sessions").rglob("*.jsonl"))), 1)
        self.assertFalse((self.restore_root / "state_5.sqlite").exists())
        index_lines = (self.restore_root / "session_index.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(index_lines), 1)
        self.assertIn(self.session_ids[0], index_lines[0])
        launcher = (self.restore_root / "start-codex-recovery.cmd").read_text(
            encoding="utf-8"
        )
        self.assertIn(str(self.restore_root), launcher)
        self.assertNotIn(".restore-", launcher)

    def test_full_restore_copies_all_sessions_and_indexes_but_not_database(self):
        report = restore_archive(
            self.spec, self.machine_root, self.restore_root, "full"
        )
        self.assertEqual(report["sessions_restored"], 2)
        self.assertEqual(len(list((self.restore_root / "sessions").rglob("*.jsonl"))), 2)
        self.assertTrue((self.restore_root / "session_index.jsonl").exists())
        self.assertFalse((self.restore_root / "state_5.sqlite").exists())

    def test_single_archived_restore_is_activated(self):
        session_id = self.session_ids[0]
        manifest_path = self.machine_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        item = manifest["sessions"][f"codex:test-machine:{session_id}"]
        old_path = self.machine_root / item["vault_path"]
        new_relative = Path(
            str(item["vault_path"]).replace(
                "native/sessions/", "native/archived_sessions/"
            )
        )
        new_path = self.machine_root / new_relative
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_bytes(old_path.read_bytes())
        old_path.unlink()
        item["source_collection"] = "archived_sessions"
        item["vault_path"] = str(new_relative)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = restore_archive(
            self.spec,
            self.machine_root,
            self.restore_root,
            "session",
            session_id,
        )
        self.assertEqual(report["activated_archived_sessions"], 1)
        self.assertEqual(len(list((self.restore_root / "sessions").rglob("*.jsonl"))), 1)
        self.assertFalse((self.restore_root / "archived_sessions").exists())

    def test_rejects_existing_restore_root(self):
        self.restore_root.mkdir()
        with self.assertRaises(SyncError):
            restore_archive(self.spec, self.machine_root, self.restore_root, "full")

    def test_detects_tampered_archive(self):
        path = next((self.machine_root / "native").rglob("*.jsonl"))
        path.write_text("tampered", encoding="utf-8")
        with self.assertRaises(SyncError):
            restore_archive(self.spec, self.machine_root, self.restore_root, "full")

    def test_dry_run_writes_nothing(self):
        report = restore_archive(
            self.spec,
            self.machine_root,
            self.restore_root,
            "session",
            self.session_ids[0],
            True,
        )
        self.assertFalse(self.restore_root.exists())
        self.assertEqual(report["sessions_selected"], 1)


if __name__ == "__main__":
    unittest.main()
