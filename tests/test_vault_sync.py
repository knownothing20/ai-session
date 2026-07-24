from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
import uuid
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from session_vault.core import (  # noqa: E402
    derive_machine_id,
    inspect_adapter,
    sync_archive,
    vault_machine_root,
    verify_archive,
)
from session_vault.registry import build_adapter, list_adapters  # noqa: E402


class VaultSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "codex-home"
        self.vault = self.root / "vault"
        (self.source / "sessions/2026/07/20").mkdir(parents=True)
        (self.source / "archived_sessions").mkdir(parents=True)
        self.session_id = str(uuid.uuid4())
        self.session_path = (
            self.source
            / "sessions/2026/07/20"
            / f"rollout-2026-07-20T00-00-00-{self.session_id}.jsonl"
        )
        self.session_path.write_text(
            json.dumps({"type": "session_meta", "id": self.session_id}) + "\n",
            encoding="utf-8",
        )
        (self.source / "session_index.jsonl").write_text(
            json.dumps({"id": self.session_id, "thread_name": "test"}) + "\n",
            encoding="utf-8",
        )
        with closing(sqlite3.connect(self.source / "state_5.sqlite")) as db:
            db.execute("create table threads(id text primary key, title text)")
            db.execute("insert into threads values (?, ?)", (self.session_id, "test"))
            db.commit()
        self.machine_id = "test-machine"
        self.spec = build_adapter("codex", str(self.source))

    def tearDown(self):
        self.temp.cleanup()

    def test_adapters_are_discovered_independently(self):
        ids = {item["app_id"] for item in list_adapters()}
        self.assertEqual(
            ids,
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
        self.assertEqual(build_adapter("claude").app_id, "claude-code")
        self.assertEqual(build_adapter("gemini").app_id, "gemini-cli")
        self.assertEqual(build_adapter("qwen").app_id, "qwen-code")
        self.assertEqual(build_adapter("kimi").app_id, "kimi-cli")
        self.assertEqual(build_adapter("hermes").app_id, "hermes-agent")

    def test_inspect_and_layout(self):
        result = inspect_adapter(self.spec, self.vault, self.machine_id)
        self.assertEqual(result["session_files"], 1)
        self.assertEqual(result["machine_id"], self.machine_id)
        expected = vault_machine_root(
            self.vault, "codex", "test-machine"
        ).resolve()
        self.assertEqual(Path(result["planned_machine_root"]).resolve(), expected)

    def test_initial_sync_repeat_append_duplicate_and_verify(self):
        first = sync_archive(self.spec, self.vault, self.machine_id)
        self.assertEqual(first["sessions_copied"], 1)
        self.assertEqual(first["metadata_updated"], 2)

        second = sync_archive(self.spec, self.vault, self.machine_id)
        self.assertEqual(second["sessions_copied"], 0)
        self.assertEqual(second["sessions_skipped"], 1)
        self.assertEqual(second["metadata_skipped"], 2)

        with self.session_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"type": "message", "text": "continued"}) + "\n")
        third = sync_archive(self.spec, self.vault, self.machine_id)
        self.assertEqual(third["sessions_copied"], 1)
        machine_root = vault_machine_root(self.vault, "codex", self.machine_id)
        manifest = json.loads((machine_root / "manifest.json").read_text(encoding="utf-8"))
        item = next(iter(manifest["sessions"].values()))
        self.assertEqual(item["status"], "appended")
        self.assertEqual(item["revision"], 2)

        duplicate_id = str(uuid.uuid4())
        duplicate_path = self.session_path.with_name(
            f"rollout-2026-07-20T00-00-01-{duplicate_id}.jsonl"
        )
        duplicate_path.write_bytes(self.session_path.read_bytes())
        fourth = sync_archive(self.spec, self.vault, self.machine_id)
        self.assertEqual(fourth["duplicate_content_detected"], 1)

        verified = verify_archive(machine_root)
        self.assertTrue(verified["ok"], verified)
        self.assertEqual(verified["sessions_checked"], 2)
        self.assertEqual(verified["metadata_checked"], 2)

    def test_conflict_preserves_old_revision(self):
        sync_archive(self.spec, self.vault, self.machine_id)
        self.session_path.write_text(
            json.dumps({"replacement": True, "id": self.session_id}) + "\n",
            encoding="utf-8",
        )
        report = sync_archive(self.spec, self.vault, self.machine_id)
        self.assertEqual(report["session_conflicts"], 1)
        machine_root = vault_machine_root(self.vault, "codex", self.machine_id)
        conflict_files = list((machine_root / "conflicts" / self.session_id).glob("*.jsonl"))
        self.assertEqual(len(conflict_files), 1)

    def test_explicit_machine_id_has_priority(self):
        old = os.environ.get("AGENT_VAULT_MACHINE_ID")
        os.environ["AGENT_VAULT_MACHINE_ID"] = "env-machine"
        try:
            self.assertEqual(derive_machine_id("cli-machine"), "cli-machine")
            self.assertEqual(derive_machine_id(), "env-machine")
        finally:
            if old is None:
                os.environ.pop("AGENT_VAULT_MACHINE_ID", None)
            else:
                os.environ["AGENT_VAULT_MACHINE_ID"] = old


if __name__ == "__main__":
    unittest.main()
