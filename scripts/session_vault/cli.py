from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    SyncError,
    derive_machine_id,
    describe_layout,
    inspect_adapter,
    restore_archive,
    sync_archive,
    vault_machine_root,
    verify_archive,
)
from .registry import build_adapter, list_adapters


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Incrementally archive and restore local AI coding-agent sessions"
    )
    command.add_argument("--app", help="Adapter id or alias, for example codex")
    command.add_argument("--vault-root", help="Portable vault root directory")
    command.add_argument("--source-root", help="Override the adapter source root")
    command.add_argument("--machine-id", help="Stable machine folder id")
    command.add_argument("--restore-root", help="New isolated native restore directory")
    command.add_argument(
        "--restore-scope",
        choices=("session", "full"),
        default="session",
        help="Restore one session or the complete archived session set",
    )
    command.add_argument("--session-id", help="Native session ID for session restore")
    command.add_argument(
        "--mode",
        choices=("inspect", "sync", "verify", "layout", "restore", "list-apps"),
        default="inspect",
    )
    command.add_argument("--dry-run", action="store_true")
    return command


def main(argv: list[str] | None = None) -> int:
    options = parser().parse_args(argv)
    try:
        if options.mode == "list-apps":
            result = {"adapters": list_adapters()}
        else:
            if not options.app:
                raise SyncError("--app is required unless --mode list-apps is used")
            spec = build_adapter(options.app, options.source_root)
            machine_id = derive_machine_id(options.machine_id)
            vault_root = (
                Path(options.vault_root).expanduser().resolve()
                if options.vault_root
                else None
            )
            if options.mode == "inspect":
                result = inspect_adapter(spec, vault_root, machine_id)
            elif options.mode == "layout":
                if vault_root is None:
                    raise SyncError("--vault-root is required for layout")
                result = describe_layout(vault_root, spec.app_id, machine_id)
            elif options.mode == "sync":
                if vault_root is None:
                    raise SyncError("--vault-root is required for sync")
                result = sync_archive(spec, vault_root, machine_id, options.dry_run)
            elif options.mode == "restore":
                if vault_root is None:
                    raise SyncError("--vault-root is required for restore")
                if not options.restore_root:
                    raise SyncError("--restore-root is required for restore")
                machine_root = vault_machine_root(vault_root, spec.app_id, machine_id)
                result = restore_archive(
                    spec,
                    machine_root,
                    Path(options.restore_root).expanduser().resolve(),
                    options.restore_scope,
                    options.session_id,
                    options.dry_run,
                )
            else:
                if vault_root is None:
                    raise SyncError("--vault-root is required for verify")
                root = vault_machine_root(vault_root, spec.app_id, machine_id)
                result = verify_archive(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (SyncError, ValueError) as exc:
        print(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        return 130
