from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAURI_ROOT = ROOT / "desktop" / "src-tauri"


class TauriHandlerInjectionTests(unittest.TestCase):
    def test_upstream_runtime_contains_one_stable_handler_anchor(self):
        upstream = (TAURI_ROOT / "src" / "lib_upstream.rs").read_text(encoding="utf-8")
        anchor = "            force_quit_and_relaunch\n"
        self.assertEqual(upstream.count(anchor), 1)

    def test_build_script_registers_all_vault_commands(self):
        build_script = (TAURI_ROOT / "build.rs").read_text(encoding="utf-8")
        for command in (
            "get_vault_sidecar_status",
            "preview_vault_sidecar_command",
            "start_vault_sidecar_task",
            "cancel_vault_sidecar_task",
            "list_vault_sidecar_tasks",
        ):
            with self.subTest(command=command):
                self.assertIn(
                    f"crate::commands::vault_sidecar::{command}",
                    build_script,
                )
        self.assertIn("anchor_count, 1", build_script)

    def test_library_compiles_generated_runtime_only(self):
        wrapper = (TAURI_ROOT / "src" / "lib.rs").read_text(encoding="utf-8")
        self.assertIn('include!(concat!(env!("OUT_DIR")', wrapper)
        self.assertNotIn('include!("lib_upstream.rs")', wrapper)

    def test_vault_module_is_declared(self):
        modules = (TAURI_ROOT / "src" / "commands" / "mod.rs").read_text(
            encoding="utf-8"
        )
        self.assertIn("pub mod vault_sidecar;", modules)


if __name__ == "__main__":
    unittest.main()
