from __future__ import annotations

import json
import os
import shlex
import shutil
import tempfile
import uuid
from pathlib import Path

from .archive import LAYOUT_VERSION, SCHEMA_VERSION, load_manifest
from .models import AdapterSpec
from .utils import SyncError, atomic_copy, atomic_write_json, hash_file, utc_now

RESTORE_MARKER = ".agent-session-restore.json"
CODEX_RESTORE_STRATEGY = "codex-rollout-backfill"
_ALLOWED_CODEX_COLLECTIONS = {"sessions", "archived_sessions"}


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _safe_relative(value: str, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SyncError(f"Unsafe {label} path in manifest: {value}")
    return path


def _verified_source(machine_root: Path, relative: str, expected_hash: str, label: str) -> Path:
    rel = _safe_relative(relative, label)
    source = machine_root / rel
    if not _is_within(source, machine_root):
        raise SyncError(f"{label} escapes machine archive: {relative}")
    if not source.is_file():
        raise SyncError(f"Missing {label}: {source}")
    actual = hash_file(source)
    if actual != expected_hash:
        raise SyncError(
            f"{label} hash mismatch: {source} (expected {expected_hash}, got {actual})"
        )
    return source


def _session_destination(stage_root: Path, item: dict) -> Path:
    collection = item.get("source_collection")
    if collection not in _ALLOWED_CODEX_COLLECTIONS:
        raise SyncError(f"Unsupported Codex restore collection: {collection!r}")
    vault_path = _safe_relative(str(item.get("vault_path", "")), "session")
    prefix = Path("native") / collection
    try:
        native_relative = vault_path.relative_to(prefix)
    except ValueError as exc:
        raise SyncError(
            f"Session path does not match collection {collection}: {vault_path}"
        ) from exc
    if ".." in native_relative.parts:
        raise SyncError(f"Unsafe native session path: {native_relative}")
    return stage_root / collection / native_relative


def _atomic_write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(text, encoding="utf-8", newline="\n")
        if executable:
            temp_path.chmod(0o755)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_launchers(
    stage_root: Path, published_root: Path, session_id: str | None
) -> list[str]:
    command_args = ["codex", "resume"]
    if session_id:
        command_args.append(session_id)

    batch_root = str(published_root).replace("%", "%%")
    batch_command = " ".join(
        ["codex", "resume"] + ([f'"{session_id}"'] if session_id else [])
    )
    batch = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'set "CODEX_HOME={batch_root}"\r\n'
        f'set "CODEX_SQLITE_HOME={batch_root}"\r\n'
        f"{batch_command}\r\n"
    )
    _atomic_write_text(stage_root / "start-codex-recovery.cmd", batch)

    shell_root = shlex.quote(str(published_root))
    shell_command = " ".join(shlex.quote(value) for value in command_args)
    shell = (
        "#!/usr/bin/env sh\n"
        f"export CODEX_HOME={shell_root}\n"
        f"export CODEX_SQLITE_HOME={shell_root}\n"
        f"exec {shell_command}\n"
    )
    _atomic_write_text(stage_root / "start-codex-recovery.sh", shell, executable=True)
    return ["start-codex-recovery.cmd", "start-codex-recovery.sh"]


def _copy_index_full(
    machine_root: Path, stage_root: Path, name: str, item: dict
) -> str:
    source = _verified_source(
        machine_root,
        str(item.get("snapshot_path", "")),
        str(item.get("snapshot_sha256", "")),
        f"index {name}",
    )
    destination = stage_root / Path(name).name
    atomic_copy(source, destination)
    if hash_file(destination) != item.get("snapshot_sha256"):
        raise SyncError(f"Restored index hash mismatch: {destination}")
    return destination.name


def _copy_session_index_subset(
    machine_root: Path, stage_root: Path, item: dict, session_id: str
) -> str | None:
    source = _verified_source(
        machine_root,
        str(item.get("snapshot_path", "")),
        str(item.get("snapshot_sha256", "")),
        "index session_index.jsonl",
    )
    selected: list[str] = []
    for raw_line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        candidate = (
            record.get("id") or record.get("thread_id") or record.get("session_id")
        )
        if str(candidate) == session_id:
            selected.append(raw_line)
    if not selected:
        return None
    destination = stage_root / "session_index.jsonl"
    _atomic_write_text(destination, "\n".join(selected) + "\n")
    return destination.name


def _select_sessions(
    manifest: dict, scope: str, session_id: str | None
) -> list[dict]:
    values = list(manifest.get("sessions", {}).values())
    if scope == "full":
        return values
    if scope != "session":
        raise SyncError(f"Unsupported restore scope: {scope}")
    if not session_id:
        raise SyncError("--session-id is required for session restore")
    selected = [
        item
        for item in values
        if str(item.get("native_session_id")) == session_id
    ]
    if not selected:
        raise SyncError(f"Session not found in archive manifest: {session_id}")
    return selected


def restore_archive(
    spec: AdapterSpec,
    machine_root: Path,
    restore_root: Path,
    scope: str = "session",
    session_id: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Restore Codex transcripts into an isolated, rebuildable CODEX_HOME.

    SQLite snapshots are deliberately not published into the restore root. Codex
    creates a fresh database and backfills it from restored rollout JSONL files.
    """

    if spec.restore_strategy != CODEX_RESTORE_STRATEGY:
        raise SyncError(f"Adapter {spec.app_id} does not support native restore")
    machine_root = machine_root.expanduser().resolve()
    restore_root = restore_root.expanduser().resolve()
    if restore_root.exists():
        raise SyncError(f"Restore root must not already exist: {restore_root}")
    if _is_within(restore_root, spec.source_root) or _is_within(
        spec.source_root, restore_root
    ):
        raise SyncError("Restore root must be isolated from the active source directory")
    if _is_within(restore_root, machine_root) or _is_within(
        machine_root, restore_root
    ):
        raise SyncError("Restore root must be outside the vault machine directory")

    manifest = load_manifest(machine_root / "manifest.json", spec, machine_root.name)
    if manifest.get("app_id") not in {None, spec.app_id}:
        raise SyncError(
            f"Archive app mismatch: expected {spec.app_id}, got {manifest.get('app_id')}"
        )
    selected = _select_sessions(manifest, scope, session_id)
    report = {
        "schema_version": SCHEMA_VERSION,
        "layout_version": LAYOUT_VERSION,
        "app_id": spec.app_id,
        "machine_id": manifest.get("machine_id", machine_root.name),
        "scope": scope,
        "session_id": session_id,
        "machine_root": str(machine_root),
        "restore_root": str(restore_root),
        "dry_run": dry_run,
        "started_at": utc_now(),
        "sessions_selected": len(selected),
        "sessions_restored": 0,
        "indexes_restored": [],
        "sqlite_snapshots_skipped": 0,
        "restore_strategy": CODEX_RESTORE_STRATEGY,
        "database_rebuild_required": True,
        "warnings": [],
    }

    verified_sessions: list[tuple[Path, dict]] = []
    for item in selected:
        source = _verified_source(
            machine_root,
            str(item.get("vault_path", "")),
            str(item.get("sha256", "")),
            f"session {item.get('native_session_id')}",
        )
        verified_sessions.append((source, item))

    metadata = manifest.get("metadata", {})
    report["sqlite_snapshots_skipped"] = sum(
        1 for item in metadata.values() if item.get("kind") == "sqlite"
    )
    if dry_run:
        report["completed_at"] = utc_now()
        report["planned_launch_command"] = (
            f"codex resume {session_id}" if session_id else "codex resume"
        )
        return report

    restore_root.parent.mkdir(parents=True, exist_ok=True)
    stage_root = (
        restore_root.parent
        / f".{restore_root.name}.restore-{uuid.uuid4().hex[:10]}"
    )
    if stage_root.exists():
        raise SyncError(f"Unexpected staging path already exists: {stage_root}")
    stage_root.mkdir(parents=True)
    try:
        for source, item in verified_sessions:
            destination = _session_destination(stage_root, item)
            atomic_copy(source, destination)
            if hash_file(destination) != item.get("sha256"):
                raise SyncError(f"Restored session hash mismatch: {destination}")
            report["sessions_restored"] += 1

        for name, item in metadata.items():
            if item.get("kind") != "index":
                continue
            restored_name: str | None
            if scope == "session":
                restored_name = (
                    _copy_session_index_subset(
                        machine_root, stage_root, item, session_id
                    )
                    if name == "session_index.jsonl" and session_id
                    else None
                )
            else:
                restored_name = _copy_index_full(
                    machine_root, stage_root, name, item
                )
            if restored_name:
                report["indexes_restored"].append(restored_name)

        launchers = _write_launchers(
            stage_root,
            restore_root,
            session_id if scope == "session" else None,
        )
        report["launchers"] = launchers
        report["completed_at"] = utc_now()
        report["note"] = (
            "No vendor SQLite database was restored. On first launch Codex should "
            "create a fresh state database and backfill it from rollout files."
        )
        atomic_write_json(stage_root / RESTORE_MARKER, report)
        atomic_write_json(stage_root / "restore-report.json", report)
        _atomic_write_text(
            stage_root / "README-RESTORE.txt",
            "This is an isolated Codex recovery directory.\n"
            "The original Codex directory was not modified.\n"
            "No auth.json or old state SQLite database was restored.\n"
            "Run start-codex-recovery.cmd on Windows or "
            "start-codex-recovery.sh on Linux/macOS.\n",
        )
        os.replace(stage_root, restore_root)
    except Exception:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise
    report["published"] = True
    report["report_path"] = str(restore_root / "restore-report.json")
    return report
