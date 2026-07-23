from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from pathlib import Path

from .models import AdapterSpec

AdapterFactory = Callable[[str | None], AdapterSpec]
_FACTORIES: dict[str, AdapterFactory] = {}
_ALIASES: dict[str, str] = {}
_DISCOVERED = False


def register_adapter(app_id: str, *aliases: str):
    """Decorator used by independent adapter modules."""

    canonical = app_id.strip().lower()

    def decorate(factory: AdapterFactory) -> AdapterFactory:
        if canonical in _FACTORIES:
            raise RuntimeError(f"Duplicate adapter id: {canonical}")
        _FACTORIES[canonical] = factory
        for value in (canonical, *aliases):
            key = value.strip().lower()
            if key in _ALIASES and _ALIASES[key] != canonical:
                raise RuntimeError(f"Duplicate adapter alias: {key}")
            _ALIASES[key] = canonical
        return factory

    return decorate


def discover_adapters() -> None:
    """Import every module in session_vault.adapters.

    Adding support for a new application only requires placing a new .py adapter
    module in that package. No central switch statement needs editing.
    """

    global _DISCOVERED
    if _DISCOVERED:
        return
    package = importlib.import_module("session_vault.adapters")
    for module in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if module.name.rsplit(".", 1)[-1].startswith("_"):
            continue
        importlib.import_module(module.name)
    _DISCOVERED = True


def canonical_app_id(value: str) -> str:
    discover_adapters()
    key = value.strip().lower()
    try:
        return _ALIASES[key]
    except KeyError as exc:
        supported = ", ".join(sorted(_FACTORIES))
        raise ValueError(f"Unsupported app '{value}'. Supported: {supported}") from exc


def build_adapter(value: str, source_root: str | None = None) -> AdapterSpec:
    app_id = canonical_app_id(value)
    spec = _FACTORIES[app_id](source_root)
    if spec.app_id != app_id:
        raise RuntimeError(f"Adapter returned mismatched app_id: {spec.app_id} != {app_id}")
    return spec


def list_adapters() -> list[dict[str, object]]:
    discover_adapters()
    result = []
    for app_id in sorted(_FACTORIES):
        spec = _FACTORIES[app_id](None)
        result.append(
            {
                "app_id": spec.app_id,
                "display_name": spec.display_name,
                "aliases": sorted(set(spec.aliases)),
                "default_source_root": str(Path(spec.source_root)),
                "restore_strategy": spec.restore_strategy,
            }
        )
    return result
