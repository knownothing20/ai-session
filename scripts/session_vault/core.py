"""Compatibility exports for the public synchronization API."""

from .operations import describe_layout, inspect_adapter, sync_archive, verify_archive
from .restore import restore_archive
from .utils import SyncError, derive_machine_id, vault_machine_root

__all__ = [
    "SyncError",
    "derive_machine_id",
    "describe_layout",
    "inspect_adapter",
    "restore_archive",
    "sync_archive",
    "vault_machine_root",
    "verify_archive",
]
