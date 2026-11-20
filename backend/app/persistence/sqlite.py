from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..models import Mission


class SqliteIndex:
    """Secondary index for missions/events. JSON files remain source of truth for full mission bodies."""

    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir) / "shipcrew.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                template_id TEXT,
                project_id TEXT,
                artifact_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                summary_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
            CREATE INDEX IF NOT EXISTS idx_missions_updated ON missions(updated_at);
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def upsert_mission(self, mission: Mission) -> None:
        summary = {
            "id": mission.id,
            "title": mission.title,
            "status": mission.status.value
            if hasattr(mission.status, "value")
            else str(mission.status),
            "current_role": mission.current_role.value if mission.current_role else None,
            "artifact_count": len(mission.artifacts),
            "template_id": mission.template_id,
            "project_id": mission.project_id,
        }
        self._conn.execute(
            """
            INSERT INTO missions (
                id, title, status, template_id, project_id, artifact_count,
                created_at, updated_at, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                status=excluded.status,
                template_id=excluded.template_id,
                project_id=excluded.project_id,
                artifact_count=excluded.artifact_count,
                updated_at=excluded.updated_at,
                summary_json=excluded.summary_json
            """,
            (
                mission.id,
                mission.title,
                summary["status"],
                mission.template_id,
                mission.project_id,
                len(mission.artifacts),
                mission.created_at.isoformat()
                if hasattr(mission.created_at, "isoformat")
                else str(mission.created_at),
                mission.updated_at.isoformat()
                if hasattr(mission.updated_at, "isoformat")
                else str(mission.updated_at),
                json.dumps(summary, ensure_ascii=False),
            ),
        )
        self._conn.commit()

    def delete_mission(self, mission_id: str) -> None:
        self._conn.execute("DELETE FROM missions WHERE id = ?", (mission_id,))
        self._conn.commit()

    def list_summaries(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT summary_json FROM missions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                out.append(json.loads(row["summary_json"]))
            except json.JSONDecodeError:
                continue
        return out

    def count_by_status(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) AS c FROM missions GROUP BY status"
        ).fetchall()
        return {str(r["status"]): int(r["c"]) for r in rows}

    def close(self) -> None:
        self._conn.close()
