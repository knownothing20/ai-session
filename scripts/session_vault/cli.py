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
from .protocol import PROTOCOL_VERSION, ProgressCallback, SidecarEmitter, make_progress
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
    command.add_argument(
        "--output-format",
        choices=("pretty", "json", "jsonl"),
        default="pretty",
        help=(
            "pretty keeps the existing human-readable JSON output; json emits one "
            "compact final object; jsonl emits versioned sidecar lifecycle events"
        ),
    )
    command.add_argument(
        "--protocol-version",
        type=int,
        choices=(PROTOCOL_VERSION,),
        default=PROTOCOL_VERSION,
        help="Sidecar JSONL protocol version",
    )
    command.add_argument(
        "--request-id",
        help="Caller-supplied request identifier for JSONL sidecar events",
    )
    return command


def _execute(
    options: argparse.Namespace,
    progress: ProgressCallback | None = None,
) -> dict:
    if options.mode == "list-apps":
        if progress is not None:
            progress(
                make_progress(
                    "discover",
                    "Discovering supported Vault adapters",
                    current=0,
                    total=1,
                )
            )
        adapters = list_adapters()
        if progress is not None:
            progress(
                make_progress(
                    "discover",
                    "Adapter discovery complete",
                    current=1,
                    total=1,
                    details={"adapter_count": len(adapters)},
                )
            )
        return {"adapters": adapters}

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
        return inspect_adapter(spec, vault_root, machine_id, progress)
    if options.mode == "layout":
        if vault_root is None:
            raise SyncError("--vault-root is required for layout")
        return describe_layout(vault_root, spec.app_id, machine_id, progress)
    if options.mode == "sync":
        if vault_root is None:
            raise SyncError("--vault-root is required for sync")
        return sync_archive(
            spec,
            vault_root,
            machine_id,
            options.dry_run,
            progress,
        )
    if options.mode == "restore":
        if vault_root is None:
            raise SyncError("--vault-root is required for restore")
        if not options.restore_root:
            raise SyncError("--restore-root is required for restore")
        machine_root = vault_machine_root(vault_root, spec.app_id, machine_id)
        return restore_archive(
            spec,
            machine_root,
            Path(options.restore_root).expanduser().resolve(),
            options.restore_scope,
            options.session_id,
            options.dry_run,
            progress,
        )
    if vault_root is None:
        raise SyncError("--vault-root is required for verify")
    root = vault_machine_root(vault_root, spec.app_id, machine_id)
    return verify_archive(root, progress)


def _started_data(options: argparse.Namespace) -> dict:
    """Return non-secret invocation metadata suitable for a lifecycle event."""

    return {
        "app_id": options.app,
        "dry_run": bool(options.dry_run),
        "restore_scope": options.restore_scope if options.mode == "restore" else None,
        "has_vault_root": bool(options.vault_root),
        "has_source_override": bool(options.source_root),
        "has_restore_root": bool(options.restore_root),
        "has_session_id": bool(options.session_id),
    }


def _write_final(result: dict, output_format: str, *, stream=sys.stdout) -> None:
    if output_format == "json":
        print(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")),
            file=stream,
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)


def main(argv: list[str] | None = None) -> int:
    options = parser().parse_args(argv)
    emitter: SidecarEmitter | None = None
    if options.output_format == "jsonl":
        emitter = SidecarEmitter(
            options.mode,
            request_id=options.request_id,
            protocol_version=options.protocol_version,
        )
        emitter.started(_started_data(options))

    try:
        result = _execute(
            options,
            emitter.progress_callback() if emitter is not None else None,
        )
        if emitter is not None:
            if options.mode == "verify" and result.get("ok") is False:
                emitter.failed(
                    "VERIFY_FAILED",
                    f"Vault verification found {result.get('errors', 0)} integrity errors",
                    details={"report": result},
                )
                return 3
            emitter.completed(result)
        else:
            _write_final(result, options.output_format)
        return 0
    except SyncError as exc:
        if emitter is not None:
            emitter.failed("SYNC_ERROR", str(exc))
        else:
            _write_final(
                {"ok": False, "error": str(exc)},
                options.output_format,
                stream=sys.stderr,
            )
        return 2
    except ValueError as exc:
        if emitter is not None:
            emitter.failed("INVALID_ARGUMENT", str(exc))
        else:
            _write_final(
                {"ok": False, "error": str(exc)},
                options.output_format,
                stream=sys.stderr,
            )
        return 2
    except KeyboardInterrupt:
        if emitter is not None:
            emitter.failed("CANCELLED", "Operation cancelled by the caller", retryable=True)
        return 130
    except BrokenPipeError:
        # The desktop bridge may close stdout after cancellation. Avoid emitting
        # a traceback that could be mistaken for a second protocol result.
        return 130
    except Exception as exc:
        # Sidecar mode must always terminate with a parseable lifecycle event.
        # The legacy CLI retains its traceback for unexpected programming errors.
        if emitter is None:
            raise
        emitter.failed("INTERNAL_ERROR", str(exc))
        print(f"Unexpected sidecar error: {exc}", file=sys.stderr)
        return 1
