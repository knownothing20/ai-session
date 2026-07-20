from __future__ import annotations

import platform
import socket
import sqlite3
from pathlib import Path

from .archive import (
    LAYOUT_VERSION,
    SCHEMA_VERSION,
    initialize_vault,
    iter_metadata_files,
    iter_session_files,
    load_manifest,
    sqlite_snapshot,
)
from .models import AdapterSpec
from .utils import (
    SyncError,
    VaultLock,
    atomic_copy,
    atomic_write_json,
    derive_machine_id,
    hash_file,
    is_exact_prefix,
    safe_name,
    timestamp_slug,
    utc_now,
    vault_machine_root,
)


def sync_sessions(spec, machine_root, machine_id, manifest, report, dry_run):
    by_hash: dict[str, list[str]] = {}
    for key, item in manifest["sessions"].items():
        digest = item.get("sha256")
        if digest:
            by_hash.setdefault(digest, []).append(key)
    extractor = spec.session_id_extractor
    if extractor is None:
        raise SyncError(f"Adapter {spec.app_id} has no session ID extractor")

    for collection, source in iter_session_files(spec):
        report["sessions_scanned"] += 1
        native_id = extractor(source)
        key = f"{spec.app_id}:{machine_id}:{native_id}"
        destination = machine_root / "native" / safe_name(collection.name) / source.relative_to(collection.root)
        stat = source.stat()
        previous = manifest["sessions"].get(key)
        if previous and previous.get("size") == stat.st_size and previous.get("mtime_ns") == stat.st_mtime_ns and destination.exists():
            report["sessions_skipped"] += 1
            continue
        digest = hash_file(source)
        if previous and previous.get("sha256") == digest and destination.exists():
            previous.update(size=stat.st_size, mtime_ns=stat.st_mtime_ns, last_seen_at=utc_now())
            report["sessions_skipped"] += 1
            continue

        status, revision = "new", 1
        if previous:
            revision = int(previous.get("revision", 1)) + 1
            previous_path = machine_root / previous.get("vault_path", "")
            if is_exact_prefix(previous_path, source):
                status = "appended"
            else:
                status = "conflict-replaced"
                if previous_path.exists():
                    conflict_path = machine_root / "conflicts" / safe_name(native_id) / (
                        f"r{previous.get('revision', 1)}-{previous.get('sha256', 'unknown')[:12]}{previous_path.suffix}"
                    )
                    atomic_copy(previous_path, conflict_path, dry_run)
                report["session_conflicts"] += 1
        duplicates = [candidate for candidate in by_hash.get(digest, []) if candidate != key]
        if duplicates:
            report["duplicate_content_detected"] += 1
        atomic_copy(source, destination, dry_run)
        manifest["sessions"][key] = {
            "app_id": spec.app_id,
            "machine_id": machine_id,
            "native_session_id": native_id,
            "source_path": str(source),
            "source_collection": collection.name,
            "vault_path": str(destination.relative_to(machine_root)),
            "sha256": digest,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "revision": revision,
            "status": status,
            "duplicate_content_of": duplicates,
            "last_seen_at": utc_now(),
        }
        by_hash.setdefault(digest, []).append(key)
        report["sessions_copied"] += 1


def sync_metadata(spec, machine_root, manifest, report, dry_run):
    latest_root = machine_root / "metadata/latest"
    history_root = machine_root / "metadata/history"
    for source, kind in iter_metadata_files(spec):
        destination = latest_root / source.name
        previous = manifest["metadata"].get(source.name)
        stat = source.stat()
        if previous and previous.get("source_size") == stat.st_size and previous.get("source_mtime_ns") == stat.st_mtime_ns and destination.exists():
            report["metadata_skipped"] += 1
            continue
        try:
            if kind == "sqlite":
                if destination.exists() and not dry_run:
                    atomic_copy(destination, history_root / timestamp_slug() / source.name)
                snapshot_hash = sqlite_snapshot(source, destination, dry_run)
                method = "sqlite-backup-api"
            else:
                source_hash = hash_file(source)
                if previous and previous.get("snapshot_sha256") == source_hash and destination.exists():
                    previous.update(source_size=stat.st_size, source_mtime_ns=stat.st_mtime_ns, last_seen_at=utc_now())
                    report["metadata_skipped"] += 1
                    continue
                if destination.exists() and not dry_run:
                    atomic_copy(destination, history_root / timestamp_slug() / source.name)
                atomic_copy(source, destination, dry_run)
                snapshot_hash, method = source_hash, "atomic-copy"
        except Exception as exc:
            report["metadata_failed"] += 1
            report["warnings"].append(f"{source.name}: {exc}")
            continue
        manifest["metadata"][source.name] = {
            "kind": kind,
            "source_path": str(source),
            "source_size": stat.st_size,
            "source_mtime_ns": stat.st_mtime_ns,
            "snapshot_path": str(destination.relative_to(machine_root)),
            "snapshot_sha256": snapshot_hash,
            "snapshot_at": utc_now(),
            "method": method,
        }
        report["metadata_updated"] += 1


def inspect_adapter(spec: AdapterSpec, vault_root=None, machine_id=None):
    entries = list(iter_session_files(spec))
    categories: dict[str, int] = {}
    for collection, _ in entries:
        categories[collection.name] = categories.get(collection.name, 0) + 1
    resolved = derive_machine_id(machine_id)
    result = {
        "app_id": spec.app_id,
        "display_name": spec.display_name,
        "aliases": list(spec.aliases),
        "source_root": str(spec.source_root),
        "source_exists": spec.source_root.exists(),
        "machine_id": resolved,
        "session_files": len(entries),
        "session_collections": categories,
        "session_bytes": sum(path.stat().st_size for _, path in entries),
        "sqlite_files": [str(path) for path, kind in iter_metadata_files(spec) if kind == "sqlite"],
        "index_files": [str(path) for path, kind in iter_metadata_files(spec) if kind == "index"],
        "excluded_by_default": list(spec.excluded_names),
    }
    if vault_root is not None:
        result["planned_machine_root"] = str(vault_machine_root(vault_root, spec.app_id, resolved))
    return result


def verify_archive(machine_root: Path) -> dict:
    manifest_path = machine_root / "manifest.json"
    if not manifest_path.exists():
        raise SyncError(f"Manifest does not exist: {manifest_path}")
    placeholder = AdapterSpec("unknown", "unknown", (), Path("."), ())
    manifest = load_manifest(manifest_path, placeholder, machine_root.name)
    details, session_count, metadata_count = [], 0, 0
    for key, item in manifest["sessions"].items():
        session_count += 1
        path = machine_root / item["vault_path"]
        if not path.exists():
            details.append(f"missing session: {key}: {path}")
        elif hash_file(path) != item.get("sha256"):
            details.append(f"session hash mismatch: {key}: {path}")
    for name, item in manifest["metadata"].items():
        metadata_count += 1
        path = machine_root / item["snapshot_path"]
        if not path.exists():
            details.append(f"missing metadata: {name}: {path}")
            continue
        if hash_file(path) != item.get("snapshot_sha256"):
            details.append(f"metadata hash mismatch: {name}: {path}")
            continue
        if item.get("kind") == "sqlite":
            try:
                with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
                    check = db.execute("PRAGMA quick_check").fetchone()
                if not check or check[0] != "ok":
                    details.append(f"SQLite quick_check failed: {name}: {path}")
            except sqlite3.Error as exc:
                details.append(f"SQLite open failed: {name}: {path}: {exc}")
    return {"ok": not details, "sessions_checked": session_count, "metadata_checked": metadata_count, "errors": len(details), "details": details}


def sync_archive(spec, vault_root, machine_id=None, dry_run=False):
    if not spec.source_root.exists():
        raise SyncError(f"Source root does not exist: {spec.source_root}")
    resolved = derive_machine_id(machine_id)
    initialize_vault(vault_root, dry_run)
    machine_root = vault_machine_root(vault_root, spec.app_id, resolved)
    manifest_path = machine_root / "manifest.json"
    report = {
        "schema_version": SCHEMA_VERSION,
        "layout_version": LAYOUT_VERSION,
        "app_id": spec.app_id,
        "machine_id": resolved,
        "source_root": str(spec.source_root),
        "vault_root": str(vault_root),
        "machine_root": str(machine_root),
        "dry_run": dry_run,
        "started_at": utc_now(),
        "sessions_scanned": 0,
        "sessions_copied": 0,
        "sessions_skipped": 0,
        "session_conflicts": 0,
        "duplicate_content_detected": 0,
        "metadata_updated": 0,
        "metadata_skipped": 0,
        "metadata_failed": 0,
        "warnings": [],
    }
    with VaultLock(machine_root / ".sync.lock", dry_run):
        manifest = load_manifest(manifest_path, spec, resolved)
        sync_sessions(spec, machine_root, resolved, manifest, report, dry_run)
        sync_metadata(spec, machine_root, manifest, report, dry_run)
        manifest.update(schema_version=SCHEMA_VERSION, layout_version=LAYOUT_VERSION, app_id=spec.app_id, machine_id=resolved, source_root=str(spec.source_root), updated_at=utc_now())
        atomic_write_json(manifest_path, manifest, dry_run)
        atomic_write_json(machine_root / "machine.json", {"machine_id": resolved, "hostname": socket.gethostname(), "platform": platform.platform(), "architecture": platform.machine(), "updated_at": utc_now()}, dry_run)
        report["completed_at"] = utc_now()
        if not dry_run:
            report_root = machine_root / "reports"
            atomic_write_json(report_root / f"sync-{timestamp_slug()}.json", report)
            atomic_write_json(report_root / "latest.json", report)
    return report


def describe_layout(vault_root: Path, app_id: str, machine_id: str) -> dict:
    root = vault_machine_root(vault_root, app_id, machine_id)
    return {
        "vault_root": str(vault_root), "app_id": app_id, "machine_id": machine_id,
        "machine_root": str(root),
        "paths": {
            "sessions": str(root / "native/<collection>/..."),
            "latest_metadata": str(root / "metadata/latest"),
            "metadata_history": str(root / "metadata/history/<timestamp>"),
            "conflicts": str(root / "conflicts/<session_id>"),
            "reports": str(root / "reports"),
            "manifest": str(root / "manifest.json"),
            "machine_info": str(root / "machine.json"),
        },
    }
