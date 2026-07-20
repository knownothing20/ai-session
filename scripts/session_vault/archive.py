from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Iterator

from .models import AdapterSpec, SessionCollection
from .utils import SyncError, atomic_write_json, hash_file, utc_now

SCHEMA_VERSION = 2
LAYOUT_VERSION = 1


def _matches_any(path: Path, patterns: tuple[str, ...]) -> bool:
    return any(path.match(pattern) for pattern in patterns)


def iter_session_files(spec: AdapterSpec) -> Iterator[tuple[SessionCollection, Path]]:
    for collection in spec.collections:
        if not collection.root.exists():
            continue
        suffixes = {suffix.lower() for suffix in collection.suffixes}
        seen: set[Path] = set()
        for pattern in collection.include_patterns:
            for path in collection.root.glob(pattern):
                if path in seen or not path.is_file():
                    continue
                seen.add(path)
                if path.suffix.lower() not in suffixes:
                    continue
                relative = path.relative_to(collection.root)
                if _matches_any(relative, collection.exclude_patterns):
                    continue
                yield collection, path


def iter_metadata_files(spec: AdapterSpec) -> Iterator[tuple[Path, str]]:
    seen: set[Path] = set()
    excluded = set(spec.excluded_names)
    for pattern in spec.sqlite_patterns:
        for path in spec.source_root.glob(pattern):
            if path.is_file() and path.name not in excluded and path not in seen:
                seen.add(path)
                yield path, "sqlite"
    for filename in spec.index_files:
        path = spec.source_root / filename
        if path.is_file() and path.name not in excluded and path not in seen:
            seen.add(path)
            yield path, "index"


def empty_manifest(spec: AdapterSpec, machine_id: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "layout_version": LAYOUT_VERSION,
        "app_id": spec.app_id,
        "machine_id": machine_id,
        "source_root": str(spec.source_root),
        "sessions": {},
        "metadata": {},
    }


def load_manifest(path: Path, spec: AdapterSpec, machine_id: str) -> dict:
    if not path.exists():
        return empty_manifest(spec, machine_id)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"Cannot read manifest {path}: {exc}") from exc
    schema = manifest.get("schema_version", 1)
    if schema not in {1, SCHEMA_VERSION}:
        raise SyncError(f"Unsupported manifest schema {schema}: {path}")
    if schema == 1:
        manifest["schema_version"] = SCHEMA_VERSION
        manifest.setdefault("layout_version", LAYOUT_VERSION)
    manifest.setdefault("sessions", {})
    manifest.setdefault("metadata", {})
    return manifest


def initialize_vault(vault_root: Path, dry_run: bool) -> None:
    marker = vault_root / "vault.json"
    if marker.exists():
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SyncError(f"Invalid vault marker {marker}: {exc}") from exc
        if data.get("type") != "agent-session-vault":
            raise SyncError(f"Directory is not an Agent Session Vault: {vault_root}")
        return
    if vault_root.exists() and any(vault_root.iterdir()):
        raise SyncError(
            f"Refusing to initialize non-empty directory without vault.json: {vault_root}"
        )
    atomic_write_json(
        marker,
        {
            "schema_version": SCHEMA_VERSION,
            "layout_version": LAYOUT_VERSION,
            "type": "agent-session-vault",
            "created_at": utc_now(),
        },
        dry_run,
    )


def sqlite_snapshot(source: Path, destination: Path, dry_run: bool) -> str:
    if dry_run:
        return "dry-run"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temp_path = Path(temp_name)
    temp_path.unlink(missing_ok=True)
    try:
        source_uri = f"file:{source.as_posix()}?mode=ro"
        with sqlite3.connect(source_uri, uri=True, timeout=30) as src_db:
            with sqlite3.connect(temp_path) as dst_db:
                src_db.backup(dst_db)
                result = dst_db.execute("PRAGMA quick_check").fetchone()
                if not result or result[0] != "ok":
                    raise SyncError(f"SQLite quick_check failed: {source}")
        digest = hash_file(temp_path)
        os.replace(temp_path, destination)
        return digest
    finally:
        temp_path.unlink(missing_ok=True)
