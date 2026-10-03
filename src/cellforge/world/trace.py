"""Append-only, hash-chained record of an agent episode."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class TraceRecorder:
    """Stores screenshots and a JSONL log; each entry commits to the previous one.

    ``trace_sha256`` covers actions, screenshot digests and notes but not
    timestamps, so replaying identical behaviour yields an identical hash.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._log = self.directory / "trace.jsonl"
        self._head = hashlib.sha256(b"cellforge-trace-v1").hexdigest()

    @property
    def trace_sha256(self) -> str:
        return self._head

    def record(
        self, step: int, action: dict[str, Any], screenshot: bytes | None, note: str = ""
    ) -> None:
        shot_digest = hashlib.sha256(screenshot).hexdigest() if screenshot else None
        if screenshot:
            (self.directory / f"step_{step:04d}.png").write_bytes(screenshot)
        core = {
            "step": step,
            "action": action,
            "screenshot_sha256": shot_digest,
            "note": note,
            "prev": self._head,
        }
        self._head = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        entry = {**core, "entry_sha256": self._head, "unix_time": time.time()}
        with self._log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
