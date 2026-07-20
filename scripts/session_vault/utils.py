from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import tempfile
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


class SyncError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def timestamp_slug() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "unknown"


def derive_machine_id(explicit: str | None = None) -> str:
    override = explicit or os.getenv("AGENT_VAULT_MACHINE_ID")
    if override:
        return safe_name(override)
    username = os.getenv("USERNAME") or os.getenv("USER") or "user"
    identity = "|".join(
        (socket.gethostname(), platform.system(), platform.machine(), username)
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    return f"{safe_name(socket.gethostname())}-{digest}"


def vault_machine_root(vault_root: Path, app_id: str, machine_id: str) -> Path:
    return vault_root / "apps" / safe_name(app_id) / "machines" / safe_name(machine_id)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def is_exact_prefix(old_path: Path, new_path: Path) -> bool:
    if not old_path.exists() or old_path.stat().st_size > new_path.stat().st_size:
        return False
    with old_path.open("rb") as old, new_path.open("rb") as new:
        for block in iter(lambda: old.read(CHUNK_SIZE), b""):
            if new.read(len(block)) != block:
                return False
    return True


def atomic_copy(source: Path, destination: Path, dry_run: bool = False) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: object, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


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
            if age < 12 * 3600:
                raise SyncError(f"Vault is locked: {self.path}")
            self.path.unlink(missing_ok=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SyncError(f"Vault is locked: {self.path}") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "created_at": utc_now()}, stream)
        self.acquired = True
        return self

    def __exit__(self, *_args):
        if self.acquired:
            self.path.unlink(missing_ok=True)
