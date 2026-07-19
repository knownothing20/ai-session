#!/usr/bin/env python3
"""Portable incremental archive tool for local AI-agent sessions.

V0.1 ships with a Codex adapter and a conservative Claude Code adapter.
It never modifies the source application's files or databases.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

SCHEMA_VERSION = 1
LOCK_STALE_HOURS = 12
CHUNK = 1024 * 1024


class SyncError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip("-") or "unknown"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def files_equal_prefix(old_path: Path, new_path: Path) -> bool:
    """Return True when old_path is an exact byte prefix of new_path."""
    try:
        if old_path.stat().st_size > new_path.stat().st_size:
            return False
        with old_path.open("rb") as old, new_path.open("rb") as new:
            while True:
                a = old.read(CHUNK)
                if not a:
                    return True
                b = new.read(len(a))
                if a != b:
                    return False
    except OSError:
        return False


def atomic_copy(src: Path, dst: Path, dry_run: bool = False) -> None:
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_write_json(path: Path, data: object, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def machine_id() -> str:
    override = os.environ.get("AGENT_VAULT_MACHINE_ID")
    if override:
        return slug(override)
    raw = "|".join([
        socket.gethostname(),
        platform.system(),
        platform.machine(),
        os.environ.get("USERNAME") or os.environ.get("USER") or "unknown-user",
    ])
    short = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return f"{slug(socket.gethostname())}-{short}"


@dataclass
class Adapter:
    app_id: str
    display_name: str
    root: Path
    session_roots: list[tuple[str, Path]]
    sqlite_patterns: list[str] = field(default_factory=list)
    index_files: list[str] = field(default_factory=list)
    excluded_names: set[str] = field(default_factory=set)

    def session_files(self) -> Iterable[tuple[str, Path, Path]]:
        for category, root in self.session_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".jsonl", ".json"}:
                    yield category, root, path

    def sqlite_files(self) -> Iterable[Path]:
        found: set[Path] = set()
        for pattern in self.sqlite_patterns:
            for path in self.root.glob(pattern):
                if path.is_file() and path.name not in self.excluded_names and path not in found:
                    found.add(path)
                    yield path

    def indexes(self) -> Iterable[Path]:
        for name in self.index_files:
            path = self.root / name
            if path.is_file() and path.name not in self.excluded_names:
                yield path

    def native_session_id(self, path: Path) -> str:
        # First use a UUID-like suffix in common transcript filenames.
        match = re.search(
            r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
            path.stem,
        )
        if match:
            return match.group(1).lower()

        # Then inspect a few JSONL records for common metadata shapes.
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                for _ in range(12):
                    line = f.readline()
                    if not line:
                        break
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    candidate = find_session_id(obj)
                    if candidate:
                        return str(candidate)
        except OSError:
            pass

        # Stable fallback: relative path, not title or timestamp.
        return f"path:{path.as_posix()}"


def find_session_id(obj: object) -> Optional[str]:
    if isinstance(obj, dict):
        # Prefer explicit session/thread ids in metadata-shaped objects.
        for key in ("session_id", "sessionId", "thread_id", "threadId"):
            value = obj.get(key)
            if isinstance(value, str) and value:
                return value
        obj_type = obj.get("type")
        if obj_type in {"session_meta", "sessionMeta", "session"}:
            for key in ("id", "uuid"):
                value = obj.get(key)
                if isinstance(value, str) and value:
                    return value
        for key in ("payload", "item", "meta", "message"):
            if key in obj:
                found = find_session_id(obj[key])
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj[:8]:
            found = find_session_id(item)
            if found:
                return found
    return None


def resolve_codex_root(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def resolve_claude_root(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (Path.home() / ".claude").resolve()


def build_adapter(app: str, source_root: Optional[str]) -> Adapter:
    if app == "codex":
        root = resolve_codex_root(source_root)
        return Adapter(
            app_id="codex",
            display_name="Codex",
            root=root,
            session_roots=[
                ("sessions", root / "sessions"),
                ("archived_sessions", root / "archived_sessions"),
            ],
            sqlite_patterns=["state_*.sqlite", "state.sqlite"],
            index_files=["session_index.jsonl", "external_agent_session_imports.json"],
            excluded_names={"auth.json", "logs_2.sqlite"},
        )
    if app in {"claude", "claude-code"}:
        root = resolve_claude_root(source_root)
        return Adapter(
            app_id="claude-code",
            display_name="Claude Code",
            root=root,
            session_roots=[("projects", root / "projects")],
            sqlite_patterns=[],
            index_files=["history.jsonl"],
            excluded_names=set(),
        )
    raise SyncError(
        f"Unsupported app '{app}'. V0.1 supports codex and claude-code. "
        "Create and approve a new adapter before syncing another application."
    )


class VaultLock:
    def __init__(self, path: Path, dry_run: bool):
        self.path = path
        self.dry_run = dry_run
        self.acquired = False

    def __enter__(self):
        if self.dry_run:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            age = dt.datetime.now().timestamp() - self.path.stat().st_mtime
            if age < LOCK_STALE_HOURS * 3600:
                raise SyncError(f"Vault is locked: {self.path}")
            self.path.unlink(missing_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps({"pid": os.getpid(), "created_at": utc_now()}))
            self.acquired = True
            return self
        except FileExistsError as exc:
            raise SyncError(f"Vault is locked: {self.path}") from exc

    def __exit__(self, exc_type, exc, tb):
        if self.acquired:
            self.path.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "updated_at": None,
            "sessions": {},
            "metadata": {},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"Cannot read manifest: {path}: {exc}") from exc
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SyncError(f"Unsupported manifest schema in {path}")
    data.setdefault("sessions", {})
    data.setdefault("metadata", {})
    return data


def init_vault(vault_root: Path, dry_run: bool) -> None:
    marker = vault_root / "vault.json"
    if not marker.exists():
        atomic_write_json(
            marker,
            {
                "schema_version": SCHEMA_VERSION,
                "type": "agent-session-vault",
                "created_at": utc_now(),
                "notes": "Portable archive. Native app sources are read-only.",
            },
            dry_run,
        )


def snapshot_sqlite(src: Path, dst: Path, dry_run: bool) -> tuple[str, str]:
    """Create a consistent SQLite snapshot using Python's SQLite backup API."""
    if dry_run:
        return "dry-run", "planned"
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    tmp.unlink(missing_ok=True)  # sqlite wants to create/open it itself
    try:
        source_uri = f"file:{src.as_posix()}?mode=ro"
        with sqlite3.connect(source_uri, uri=True, timeout=30) as source:
            with sqlite3.connect(tmp) as target:
                source.backup(target)
                check = target.execute("PRAGMA quick_check").fetchone()
                if not check or check[0] != "ok":
                    raise SyncError(f"SQLite quick_check failed for {src}: {check}")
        digest = sha256_file(tmp)
        os.replace(tmp, dst)
        return digest, "sqlite-backup-api"
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def copy_metadata_file(
    src: Path,
    latest_dir: Path,
    history_root: Path,
    manifest: dict,
    report: dict,
    dry_run: bool,
    sqlite_mode: bool,
) -> None:
    dst = latest_dir / src.name
    old = manifest["metadata"].get(src.name)
    src_digest = sha256_file(src) if not dry_run else "dry-run"
    if old and old.get("source_sha256") == src_digest and dst.exists():
        report["metadata_skipped"] += 1
        return

    if dst.exists() and old and not dry_run:
        hist = history_root / stamp() / src.name
        hist.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, hist)

    method = "atomic-copy"
    if sqlite_mode:
        try:
            snapshot_digest, method = snapshot_sqlite(src, dst, dry_run)
        except Exception as exc:
            report["warnings"].append(
                f"SQLite snapshot failed for {src.name}: {exc}. Source left untouched."
            )
            report["metadata_failed"] += 1
            return
    else:
        atomic_copy(src, dst, dry_run)
        snapshot_digest = src_digest

    manifest["metadata"][src.name] = {
        "source_path": str(src),
        "source_sha256": src_digest,
        "snapshot_sha256": snapshot_digest,
        "snapshot_path": str(dst.relative_to(latest_dir.parent.parent)),
        "snapshot_at": utc_now(),
        "method": method,
    }
    report["metadata_updated"] += 1


def sync_sessions(
    adapter: Adapter,
    app_machine_root: Path,
    manifest: dict,
    report: dict,
    dry_run: bool,
) -> None:
    hash_to_keys: dict[str, list[str]] = {}
    for key, item in manifest["sessions"].items():
        digest = item.get("sha256")
        if digest:
            hash_to_keys.setdefault(digest, []).append(key)

    for category, source_base, src in adapter.session_files():
        report["sessions_scanned"] += 1
        native_id = adapter.native_session_id(src)
        key = f"{adapter.app_id}:{machine_id()}:{native_id}"
        rel = src.relative_to(source_base)
        dst = app_machine_root / "native" / category / rel
        st = src.stat()
        old = manifest["sessions"].get(key)

        if (
            old
            and old.get("size") == st.st_size
            and old.get("mtime_ns") == st.st_mtime_ns
            and dst.exists()
        ):
            report["sessions_skipped"] += 1
            continue

        digest = sha256_file(src)
        if old and old.get("sha256") == digest and dst.exists():
            old.update({"size": st.st_size, "mtime_ns": st.st_mtime_ns, "last_seen_at": utc_now()})
            report["sessions_skipped"] += 1
            continue

        status = "new"
        revision = 1
        if old:
            revision = int(old.get("revision", 1)) + 1
            previous = app_machine_root / old.get("vault_path", "")
            if previous.exists() and files_equal_prefix(previous, src):
                status = "appended"
            else:
                status = "conflict-replaced"
                if previous.exists() and not dry_run:
                    conflict = (
                        app_machine_root
                        / "conflicts"
                        / slug(native_id)
                        / f"r{old.get('revision', 1)}-{old.get('sha256', 'unknown')[:12]}{previous.suffix}"
                    )
                    conflict.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(previous, conflict)
                report["session_conflicts"] += 1

        duplicates = [k for k in hash_to_keys.get(digest, []) if k != key]
        if duplicates:
            report["duplicate_content_detected"] += 1

        atomic_copy(src, dst, dry_run)
        manifest["sessions"][key] = {
            "app_id": adapter.app_id,
            "machine_id": machine_id(),
            "native_session_id": native_id,
            "source_path": str(src),
            "source_category": category,
            "vault_path": str(dst.relative_to(app_machine_root)),
            "sha256": digest,
            "size": st.st_size,
            "mtime_ns": st.st_mtime_ns,
            "revision": revision,
            "status": status,
            "duplicate_content_of": duplicates,
            "last_seen_at": utc_now(),
        }
        hash_to_keys.setdefault(digest, []).append(key)
        report["sessions_copied"] += 1


def inspect(adapter: Adapter) -> dict:
    session_count = 0
    total_bytes = 0
    categories: dict[str, int] = {}
    for category, _, path in adapter.session_files():
        session_count += 1
        categories[category] = categories.get(category, 0) + 1
        try:
            total_bytes += path.stat().st_size
        except OSError:
            pass
    return {
        "app_id": adapter.app_id,
        "display_name": adapter.display_name,
        "source_root": str(adapter.root),
        "source_exists": adapter.root.exists(),
        "session_files": session_count,
        "session_categories": categories,
        "session_bytes": total_bytes,
        "sqlite_files": [str(p) for p in adapter.sqlite_files()],
        "index_files": [str(p) for p in adapter.indexes()],
        "excluded_by_default": sorted(adapter.excluded_names),
    }


def verify(app_machine_root: Path) -> dict:
    manifest_path = app_machine_root / "manifest.json"
    manifest = load_manifest(manifest_path)
    checked = missing = mismatched = 0
    details: list[str] = []
    for key, item in manifest["sessions"].items():
        checked += 1
        path = app_machine_root / item["vault_path"]
        if not path.exists():
            missing += 1
            details.append(f"missing: {key}: {path}")
            continue
        digest = sha256_file(path)
        if digest != item.get("sha256"):
            mismatched += 1
            details.append(f"hash mismatch: {key}: {path}")
    return {
        "checked": checked,
        "missing": missing,
        "mismatched": mismatched,
        "ok": missing == 0 and mismatched == 0,
        "details": details,
    }


def run_sync(adapter: Adapter, vault_root: Path, dry_run: bool) -> dict:
    init_vault(vault_root, dry_run)
    mid = machine_id()
    app_machine_root = vault_root / "apps" / adapter.app_id / "machines" / mid
    report = {
        "schema_version": SCHEMA_VERSION,
        "app_id": adapter.app_id,
        "machine_id": mid,
        "source_root": str(adapter.root),
        "vault_root": str(vault_root),
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
    if not adapter.root.exists():
        raise SyncError(f"Source root does not exist: {adapter.root}")

    lock_path = app_machine_root / ".sync.lock"
    with VaultLock(lock_path, dry_run):
        manifest_path = app_machine_root / "manifest.json"
        manifest = load_manifest(manifest_path)
        sync_sessions(adapter, app_machine_root, manifest, report, dry_run)

        latest_dir = app_machine_root / "metadata" / "latest"
        history_root = app_machhine_root / "metadata" / "history"
        for src in adapter.sqlite_files():
            copy_metadata_file(
                src, latest_dir, history_root, manifest, report, dry_run, sqlite_mode=True
            )
        for src in adapter.indexes():
            copy_metadata_file(
                src, latest_dir, history_root, manifest, report, dry_run, sqlite_mode=False
            )

        manifest["updated_at"] = utc_now()
        manifest["app_id"] = adapter.app_id
        manifest["machine_id"] = mid
        manifest["source_root"] = str(adapter.root)
        atomic_write_json(manifest_path, manifest, dry_run)

        report["completed_at"] = utc_now()
        if not dry_run:
            reports_dir = app_machine_root / "reports"
            atomic_write_json(reports_dir / f"sync-{stamp()}.json", report, False)
            atomic_write_json(reports_dir / "latest.json", report, False)
    return report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Incrementally archive local AI-agent sessions")
    p.add_argument("--app", required=True, choices=["codex", "claude", "claude-code"])
    p.add_argument("--vault-root", help="Portable Agent Session Vault root")
    p.add_argument("--source-root", help="Override the native application data root")
    p.add_argument("--mode", choices=["inspect", "sync", "verify"], default="inspect")
    p.add_argument("--dry-run", action="store_true", help="Plan without writing")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        adapter = build_adapter(args.app, args.source_root)
        if args.mode == "inspect":
            result = inspect(adapter)
        else:
            if not args.vault_root:
                raise SyncError("--vault-root is required for sync and verify")
            vault_root = Path(args.vault_root).expanduser().resolve()
            app_machine_root = vault_root / "apps" / adapter.app_id / "machines" / machine_id()
            if args.mode == "verify":
                result = verify(app_machine_root)
            else:
                result = run_sync(adapter, vault_root, args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SyncError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": "Interrupted"}), file=sys.stderr)
        retW&‚3 ††¶ñbıˆÊ÷UıÚ”“%ıˆ÷ñÂıÚ#†¢&ó6R7ó7FV‘WÜóBÜ÷ñ‚Çíê