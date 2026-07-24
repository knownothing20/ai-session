from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from session_vault.core import sync_archive, vault_machine_root  # noqa: E402
from session_vault.registry import build_adapter  # noqa: E402


class SensitiveExclusionTests(unittest.TestCase):
    def test_codex_credentials_and_logs_never_enter_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "codex-home"
            vault = root / "vault"
            session_id = str(uuid.uuid4())
            session = (
                source
                / "sessions"
                / "2026"
                / "07"
                / "24"
                / f"rollout-2026-07-24T00-00-00-{session_id}.jsonl"
            )
            session.parent.mkdir(parents=True)
            session.write_text(
                json.dumps({"type": "session_meta", "id": session_id}) + "\n",
                encoding="utf-8",
            )
            (source / "auth.json").write_text(
                json.dumps({"access_token": "never-copy-this"}),
                encoding="utf-8",
            )
            with closing(sqlite3.connect(source / "logs_2.sqlite")) as logs:
                logs.execute("CREATE TABLE secrets(value TEXT)")
                logs.execute("INSERT INTO secrets VALUES ('never-copy-this')")
                logs.commit()
            (source / "session_index.jsonl").write_text(
                json.dumps({"id": session_id}) + "\n",
                encoding="utf-8",
            )

            spec = build_adapter("codex", str(source))
            report = sync_archive(spec, vault, "security-test")
            self.assertEqual(report["sessions_copied"], 1)
            machine_root = vault_machine_root(vault, "codex", "security-test")
            all_files = [path.relative_to(machine_root).as_posix() for path in machine_root.rglob("*") if path.is_file()]
            self.assertFalse(any(path.endswith("auth.json") for path in all_files), all_files)
            self.assertFalse(any(path.endswith("logs_2.sqlite") for path in all_files), all_files)
            for path in machine_root.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    contents = path.read_bytes()
                except OSError:
                    continue
                self.assertNotIn(b"never-copy-this", contents, str(path))

    def test_sidecar_started_metadata_does_not_echo_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            secret_path = Path(temp) / "private-user-path"
            result = __import__("subprocess").run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "vault_sync.py"),
                    "--mode",
                    "inspect",
                    "--app",
                    "codex",
                    "--source-root",
                    str(secret_path),
                    "--vault-root",
                    str(Path(temp) / "vault"),
                    "--output-format",
                    "jsonl",
                    "--request-id",
                    "security-request",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            first = json.loads(result.stdout.splitlines()[0])
            serialized = json.dumps(first, ensure_ascii=False)
            self.assertEqual(first["event"], "started")
            self.assertNotIn(str(secret_path), serialized)
            self.assertTrue(first["data"]["has_source_override"])
            self.assertTrue(first["data"]["has_vault_root"])


if __name__ == "__main__":
    unittest.main()
