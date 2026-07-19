#!/usr/bin/env python3
"""Incrementally archive local AI-agent sessions to a portable vault."""
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
from pathlib import Path
from typing import Iterator

SCHEMA = 1
CHUNK = 1024 * 1024
UUID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)


class SyncError(RuntimeError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "unknown"


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def is_prefix(old: Path, new: Path) -> bool:
    if not old.exists() or old.stat().st_size > new.stat().st_size:
        return False
    with old.open("rb") as a, new.open("rb") as b:
        for block in iter(lambda: a.read(CHUNK), b""):
            if b.read(len(block)) != block:
                return False
    return True


def atomic_copy(src: Path, dst: Path, dry: bool = False) -> None:
    if dry:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)


def write_json(path: Path, value: object, dry: bool = False) -> None:
    if dry:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def machine_id() -> str:
    override = os.getenv("AGENT_VAULT_MACHINE_ID")
    if override:
        return slug(override)
    raw = "|".join((socket.gethostname(), platform.system(), platform.machine(), os.getenv("USERNAME") or os.getenv("USER") or "user"))
    return f"{slug(socket.gethostname())}-{hashlib.sha256(raw.encode()).hexdigest()[:10]}"


def adapter(app: str, source: str | None) -> dict:
    if app == "codex":
        root = Path(source or os.getenv("CODEX_HOME") or Path.home() / ".codex").expanduser().resolve()
        return {
            "id": "codex", "name": "Codex", "root": root,
            "sessions": [("sessions", root / "sessions"), ("archived_sessions", root / "archived_sessions")],
            "sqlite": ["state_*.sqlite", "state.sqlite"],
            "indexes": ["session_index.jsonl", "external_agent_session_imports.json"],
            "excluded": ["auth.json", "logs_2.sqlite"],
        }
    if app in {"claude", "claude-code"}:
        root = Path(source or Path.home() / ".claude").expanduser().resolve()
        return {
            "id": "claude-code", "name": "Claude Code", "root": root,
            "sessions": [("projects", root / "projects")], "sqlite": [],
            "indexes": ["history.jsonl"], "excluded": [],
        }
    raise SyncError(f"Unsupported app: {app}")


def session_files(cfg: dict) -> Iterator[tuple[str, Path, Path]]:
    for category, base in cfg["sessions"]:
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".jsonl", ".json"}:
                    yield category, base, path


def metadata_files(cfg: dict) -> Iterator[tuple[Path, bool]]:
    seen: set[Path] = set()
    for pattern in cfg["sqlite"]:
        for path in cfg["root"].glob(pattern):
            if path.is_file() and path.name not in cfg["excluded"] and path not in seen:
                seen.add(path)
                yield path, True
    for name in cfg["indexes"]:
        path = cfg["root"] / name
        if path.is_file() and path.name not in cfg["excluded"]:
            yield path, False


def nested_id(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("session_id", "sessionId", "thread_id", "threadId"):
            if isinstance(value.get(key), str) and value[key]:
                return value[key]
        if value.get("type") in {"session_meta", "sessionMeta", "session"}:
            for key in ("id", "uuid"):
                if isinstance(value.get(key), str) and value[key]:
                    return value[key]
        for key in ("payload", "item", "meta", "message"):
            found = nested_id(value.get(key))
            if found:
                return found
    elif isinstance(value, list):
        for item in value[:8]:
            found = nested_id(item)
            if found:
                return found
    return None


def session_id(path: Path) -> str:
    match = UUID_RE.search(path.stem)
    if match:
        return match.group(1).lower()
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for _ in range(12):
                line = f.readline()
                if not line:
                    break
                try:
                    found = nested_id(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if found:
                    return found
    except OSError:
        pass
    return f"path:{path.as_posix()}"


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA, "sessions": {}, "metadata": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"Cannot read manifest {path}: {exc}") from exc
    if value.get("schema_version") != SCHEMA:
        raise SyncError(f"Unsupported manifest schema: {path}")
    value.setdefault("sessions", {})
    value.setdefault("metadata", {})
    return value


class Lock:
    def __init__(self, path: Path, dry: bool):
        self.path, self.dry, self.held = path, dry, False

    def __enter__(self):
        if self.dry:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and dt.datetime.now().timestamp() - self.path.stat().st_mtime < 12 * 3600:
            raise SyncError(f"Vault is locked: {self.path}")
        self.path.unlink(missing_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SyncError(f"Vault is locked: {self.path}") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "created_at": now()}, f)
        self.held = True
        return self

    def __exit__(self, *_):
        if self.held:
            self.path.unlink(missing_ok=True)


def sqlite_snapshot(src: Path, dst: Path, dry: bool) -> tuple[str, str]:
    if dry:
        return "dry-run", "planned"
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(name)
    tmp.unlink(missing_ok=True)
    try:
        uri = f"file:{src.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=30) as source, sqlite3.connect(tmp) as target:
            source.backup(target)
            result = target.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                raise SyncError(f"SQLite quick_check failed: {src}")
        digest = hash_file(tmp)
        os.replace(tmp, dst)
        return digest, "sqlite-backup-api"
    finally:
        tmp.unlink(missing_ok=True)


def sync_metadata(cfg: dict, root: Path, manifest: dict, report: dict, dry: bool) -> None:
    latest, history = root / "metadata/latest", root / "metadata/history"
    for src, is_sqlite in metadata_files(cfg):
        dst, old = latest / src.name, manifest["metadata"].get(src.name)
        digest = hash_file(src)
        if old and old.get("source_sha256") == digest and dst.exists():
            report["metadata_skipped"] += 1
            continue
        if dst.exists() and not dry:
            atomic_copy(dst, history / stamp() / src.name)
        try:
            snap, method = sqlite_snapshot(src, dst, dry) if is_sqlite else (digest, "atomic-copy")
            if not is_sqlite:
                atomic_copy(src, dst, dry)
        except Exception as exc:
            report["metadata_failed"] += 1
            report["warnings"].append(f"{src.name}: {exc}")
            continue
        manifest["metadata"][src.name] = {
            "source_path": str(src), "source_sha256": digest,
            "snapshot_sha256": snap, "snapshot_path": str(dst.relative_to(root)),
            "snapshot_at": now(), "method": method,
        }
        report["metadata_updated"] += 1


def sync_sessions(cfg: dict, root: Path, manifest: dict, report: dict, dry: bool) -> None:
    mid = machine_id()
    by_hash: dict[str, list[str]] = {}
    for key, item in manifest["sessions"].items():
        if item.get("sha256"):
            by_hash.setdefault(item["sha256"], []).append(key)
    for category, base, src in session_files(cfg):
        report["sessions_scanned"] += 1
        sid = session_id(src)
        key = f"{cfg['id']}:{mid}:{sid}"
        dst = root / "native" / category / src.relative_to(base)
        stat, old = src.stat(), manifest["sessions"].get(key)
        if old and old.get("size") == stat.st_size and old.get("mtime_ns") == stat.st_mtime_ns and dst.exists():
            report["sessions_skipped"] += 1
            continue
        digest = hash_file(src)
        if old and old.get("sha256") == digest and dst.exists():
            old.update(size=stat.st_size, mtime_ns=stat.st_mtime_ns, last_seen_at=now())
            report["sessions_skipped"] += 1
            continue
        status, revision = "new", 1
        if old:
            revision = int(old.get("revision", 1)) + 1
            previous = root / old.get("vault_path", "")
            if is_prefix(previous, src):
                status = "appended"
            else:
                status = "conflict-replaced"
                if previous.exists() and not dry:
                    conflict = root / "conflicts" / slug(sid) / f"r{old.get('revision', 1)}-{old.get('sha256', 'unknown')[:12]}{previous.suffix}"
                    atomic_copy(previous, conflict)
                report["session_conflicts"] += 1
        duplicates = [other for other in by_hash.get(digest, []) if other != key]
        if duplicates:
            report["duplicate_content_detected"] += 1
        atomic_copy(src, dst, dry)
        manifest["sessions"][key] = {
            "app_id": cfg["id"], "machine_id": mid, "native_session_id": sid,
            "source_path": str(src), "source_category": category,
            "vault_path": str(dst.relative_to(root)), "sha256": digest,
            "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "revision": revision, "status": status,
            "duplicate_content_of": duplicates, "last_seen_at": now(),
        }
        by_hash.setdefault(digest, []).append(key)
        report["sessions_copied"] += 1


def inspect(cfg: dict) -> dict:
    files = list(session_files(cfg))
    categories: dict[str, int] = {}
    for category, _, _ in files:
        categories[category] = categories.get(category, 0) + 1
    return {
        "app_id": cfg["id"], "display_name": cfg["name"],
        "source_root": str(cfg["root"]), "source_exists": cfg["root"].exists(),
        "session_files": len(files), "session_categories": categories,
        "session_bytes": sum(p.stat().st_size for _, _, p in files),
        "sqlite_files": [str(p) for p, flag in metadata_files(cfg) if flag],
        "index_files": [str(p) for p, flag in metadata_files(cfg) if not flag],
        "excluded_by_default": cfg["excluded"],
    }


def verify(root: Path) -> dict:
    manifest = load_manifest(root / "manifest.json")
    details, checked = [], 0
    for key, item in manifest["sessions"].items():
        checked += 1
        path = root / item["vault_path"]
        if not path.exists():
            details.append(f"missing: {key}: {path}")
        elif hash_file(path) != item.get("sha256"):
            details.append(f"hash mismatch: {key}: {path}")
    return {"checked": checked, "missing_or_mismatched": len(details), "ok": not details, "details": details}


def sync(cfg: dict, vault: Path, dry: bool) -> dict:
    if not cfg["root"].exists():
        raise SyncError(f"Source root does not exist: {cfg['root']}")
    marker = vault / "vault.json"
    if not marker.exists():
        write_json(marker, {"schema_version": SCHEMA, "type": "agent-session-vault", "created_at": now()}, dry)
    mid = machine_id()
    root = vault / "apps" / cfg["id"] / "machines" / mid
    report = {
        "schema_version": SCHEMA, "app_id": cfg["id"], "machine_id": mid,
        "source_root": str(cfg["root"]), "vault_root": str(vault), "dry_run": dry,
        "started_at": now(), "sessions_scanned": 0, "sessions_copied": 0,
        "sessions_skipped": 0, "session_conflicts": 0,
        "duplicate_content_detected": 0, "metadata_updated": 0,
        "metadata_skipped": 0, "metadata_failed": 0, "warnings": [],
    }
    with Lock(root / ".sync.lock", dry):
        manifest = load_manifest(root / "manifest.json")
        sync_sessions(cfg, root, manifest, report, dry)
        sync_metadata(cfg, root, manifest, report, dry)
        manifest.update(updated_at=now(), app_id=cfg["id"], machine_id=mid, source_root=str(cfg["root"]))
        write_json(root / "manifest.json", manifest, dry)
        report["completed_at"] = now()
        if not dry:
            write_json(root / "reports" / f"sync-{stamp()}.json", report)
            write_json(root / "reports/latest.json", report)
    return report


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incrementally archive local AI-agent sessions")
    parser.add_argument("--app", required=True, choices=["codex", "claude", "claude-code"])
    parser.add_argument("--vault-root")
    parser.add_argument("--source-root")
    parser.add_argument("--mode", choices=["inspect", "sync", "verify"], default="inspect")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    opt = args()
    try:
        cfg = adapter(opt.app, opt.source_root)
        if opt.mode == "inspect":
            result = inspect(cfg)
        else:
            if not opt.vault_root:
                raise SyncError("--vault-root is required for sync and verify")
            vault = Path(opt.vault_root).expanduser().resolve()
            root = vault / "apps" / cfg["id"] / "machines" / machine_id()
            result = verify(root) if opt.mode == "verify" else sync(cfg, vault, opt.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SyncError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
