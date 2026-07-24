from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NoGitHubActionsTests(unittest.TestCase):
    def test_repository_contains_no_workflow_files(self):
        workflow_roots = [
            ROOT / ".github" / "workflows",
            ROOT / "desktop" / ".github" / "workflows",
        ]
        files = [
            path.relative_to(ROOT).as_posix()
            for workflow_root in workflow_roots
            if workflow_root.exists()
            for path in workflow_root.rglob("*")
            if path.is_file()
        ]
        self.assertEqual(files, [], f"GitHub Actions workflows are prohibited: {files}")


if __name__ == "__main__":
    unittest.main()
