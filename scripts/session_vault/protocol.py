from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TextIO

PROTOCOL_NAME = "ai-session-vault-sidecar"
PROTOCOL_VERSION = 1
SUPPORTED_EVENT_TYPES = frozenset({"started", "progress", "completed", "failed"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_error(
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if details:
        error["details"] = details
    return error


@dataclass
class SidecarEmitter:
    """Emit one JSON object per line for the desktop sidecar bridge.

    stdout is reserved for protocol events. Human-readable diagnostics should be
    written to stderr by callers so a Rust consumer can parse stdout without
    mixing logs and structured data.
    """

    operation: str
    request_id: str | None = None
    stream: TextIO = sys.stdout
    protocol_version: int = PROTOCOL_VERSION
    _sequence: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError(
                f"Unsupported sidecar protocol version: {self.protocol_version}; "
                f"supported version is {PROTOCOL_VERSION}"
            )
        if not self.request_id:
            self.request_id = uuid.uuid4().hex

    def emit(
        self,
        event: str,
        *,
        data: dict[str, Any] | list[Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if event not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"Unsupported sidecar event type: {event}")
        if event == "failed" and error is None:
            raise ValueError("failed sidecar events require an error payload")
        if event != "failed" and error is not None:
            raise ValueError("error payload is only valid for failed events")

        self._sequence += 1
        payload: dict[str, Any] = {
            "protocol": PROTOCOL_NAME,
            "protocol_version": self.protocol_version,
            "request_id": self.request_id,
            "sequence": self._sequence,
            "timestamp": _utc_now(),
            "operation": self.operation,
            "event": event,
        }
        if data is not None:
            payload["data"] = data
        if error is not None:
            payload["error"] = error

        self.stream.write(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        self.stream.flush()
        return payload

    def started(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.emit("started", data=data)

    def progress(self, data: dict[str, Any]) -> dict[str, Any]:
        return self.emit("progress", data=data)

    def completed(self, data: dict[str, Any] | list[Any]) -> dict[str, Any]:
        return self.emit("completed", data=data)

    def failed(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.emit(
            "failed",
            error=make_error(
                code,
                message,
                retryable=retryable,
                details=details,
            ),
        )
