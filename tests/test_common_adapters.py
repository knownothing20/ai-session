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

from session_vault.archive import iter_session_files  # noqa: E402
from session_vault.core import inspect_adapter, sync_archive, vault_machine_root, verify_archive  # noqa: E402
from session_vault.registry import build_adapter  # noqa: E402


def make_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("create table sessions(id text primary key, title text)")
        db.execute("insert into sessions values ('s1', 'test')")
        db.commit()


class CommonAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_gemini_cli_discovers_only_session_files(self):
        source = self.root / "gemini"
        chats = source / "tmp" / "project-a" / "chats"
        chats.mkdir(parents=True)
        session_id = str(uuid.uuid4())
        session = chats / "session-2026-07-20-abcdef12.jsonl"
        session.write_text(json.dumps({"sessionId": session_id, "projectHash": "p"}) + "\n")
        (chats / "unrelated.json").write_text("{}")
        (source / "oauth_creds.json").write_text("secret")
        spec = build_adapter("gemini", str(source))
        files = list(iter_session_files(spec))
        self.assertEqual([path for _, path in files], [session])
        self.assertEqual(spec.session_id_extractor(session), session_id)

    def test_qwen_code_supports_active_and_archive_without_sidecars(self):
        source = self.root / "qwen"
        chats = source / "projects" / "project-a" / "chats"
        archive = chats / "archive"
        archive.mkdir(parents=True)
        session_id = str(uuid.uuid4())
        active = chats / f"{session_id}.jsonl"
        archived = archive / f"{session_id}.jsonl"
        body = json.dumps({"sessionId": session_id, "cwd": "/tmp/project"}) + "\n"
        active.write_text(body)
        archived.write_text(body)
        (chats / f"{session_id}.runtime.json").write_text("{}")
        (chats / f"{session_id}.worktree.json").write_text("{}")
        spec = build_adapter("qwen", str(source))
        files = [path for _, path in iter_session_files(spec)]
        self.assertEqual(set(files), {active, archived})
        self.assertTrue(spec.session_id_extractor(active).endswith(":active"))
        self.assertTrue(spec.session_id_extractor(archived).endswith(":archived"))

    def test_kimi_cli_keeps_context_wire_and_state_as_distinct_artifacts(self):
        source = self.root / "kimi"
        session_id = str(uuid.uuid4())
        session_dir = source / "sessions" / "workdir-hash" / session_id
        session_dir.mkdir(parents=True)
        context = session_dir / "context.jsonl"
        wire = session_dir / "wire.jsonl"
        state = session_dir / "state.json"
        context.write_text("{}\n")
        wire.write_text("{}\n")
        state.write_text(json.dumps({"custom_title": "test", "archived": False}))
        (source / "kimi.json").write_text(json.dumps({"work_dirs": []}))
        spec = build_adapter("kimi", str(source))
        files = [path for _, path in iter_session_files(spec)]
        self.assertEqual(set(files), {context, wire, state})
        ids = {spec.session_id_extractor(path) for path in files}
        self.assertEqual(len(ids), 3)
        self.assertTrue(all(value.startswith(session_id + ":") for value in ids))

    def test_aider_collects_only_known_project_history_files(self):
        source = self.root / "repo"
        source.mkdir()
        expected = {
            source / ".aider.chat.history.md",
            source / ".aider.input.history",
            source / ".aider.llm.history",
        }
        for path in expected:
            path.write_text("history")
        (source / "other.md").write_text("not aider history")
        spec = build_adapter("aider", str(source))
        files = {path for _, path in iter_session_files(spec)}
        self.assertEqual(files, expected)

    def test_sqlite_only_adapters_snapshot_and_verify(self):
        cases = {
            "opencode": (self.root / "opencode", "opencode.db"),
            "hermes": (self.root / "hermes", "state.db"),
            "goose": (self.root / "goose", "sessions/sessions.db"),
        }
        for app, (source, relative) in cases.items():
            with self.subTest(app=app):
                make_db(source / relative)
                spec = build_adapter(app, str(source))
                inspected = inspect_adapter(spec)
                self.assertEqual(inspected["session_files"], 0)
                self.assertEqual(len(inspected["sqlite_files"]), 1)
                vault = self.root / f"vault-{app}"
                report = sync_archive(spec, vault, "test-machine")
                self.assertEqual(report["metadata_updated"], 1)
                machine_root = vault_machine_root(vault, spec.app_id, "test-machine")
                verified = verify_archive(machine_root)
                self.assertTrue(verified["ok"], verified)


if __name__ == "__main__":
    unittest.main()
