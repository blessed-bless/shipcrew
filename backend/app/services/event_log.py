from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4


class EventLog:
    """Append-only mission/system event journal on disk."""

    def __init__(self, root: Path) -> None:
        self.path = root / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def emit(self, kind: str, *, mission_id: str | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "id": uuid4().hex,
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "mission_id": mission_id,
            "payload": payload or {},
        }
        line = json.dumps(event, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return event

    def tail(self, *, limit: int = 100, mission_id: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if mission_id and item.get("mission_id") != mission_id:
                continue
            rows.append(item)
            if len(rows) >= limit:
                break
        rows.reverse()
        return rows
