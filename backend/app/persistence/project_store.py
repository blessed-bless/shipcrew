from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from ..domain.projects import Project


class ProjectStore:
    def __init__(self, root: Path) -> None:
        self.path = root / "projects.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._items: dict[str, Project] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw.get("projects", []):
            project = Project.model_validate(item)
            self._items[project.id] = project

    def _persist(self) -> None:
        payload = {"projects": [p.model_dump(mode="json") for p in self._items.values()]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> list[Project]:
        with self._lock:
            return sorted(self._items.values(), key=lambda p: p.updated_at, reverse=True)

    def get(self, project_id: str) -> Project | None:
        with self._lock:
            return self._items.get(project_id)

    def save(self, project: Project) -> Project:
        with self._lock:
            project.touch()
            self._items[project.id] = project
            self._persist()
            return project

    def delete(self, project_id: str) -> bool:
        with self._lock:
            if project_id not in self._items:
                return False
            del self._items[project_id]
            self._persist()
            return True

    def attach_mission(self, project_id: str, mission_id: str) -> Project | None:
        with self._lock:
            project = self._items.get(project_id)
            if project is None:
                return None
            if mission_id not in project.mission_ids:
                project.mission_ids.append(mission_id)
            project.touch()
            self._persist()
            return project
