from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .models import Artifact, Mission


class MissionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.missions_dir = root / "missions"
        self.artifacts_dir = root / "artifacts"
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._cache: dict[str, Mission] = {}

    def list_missions(self) -> list[Mission]:
        with self._lock:
            self._hydrate()
            return sorted(self._cache.values(), key=lambda m: m.created_at, reverse=True)

    def get(self, mission_id: str) -> Mission | None:
        with self._lock:
            self._hydrate()
            return self._cache.get(mission_id)

    def save(self, mission: Mission) -> Mission:
        with self._lock:
            mission.touch()
            path = self.missions_dir / f"{mission.id}.json"
            path.write_text(mission.model_dump_json(indent=2), encoding="utf-8")
            self._cache[mission.id] = mission
            return mission

    def write_artifact(self, mission_id: str, relative_path: str, content: str, *, kind: str, created_by) -> Artifact:
        safe = relative_path.replace("\\", "/").lstrip("/")
        if ".." in safe.split("/"):
            raise ValueError(f"Unsafe artifact path: {relative_path}")
        target = self.artifacts_dir / mission_id / safe
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return Artifact(
            path=safe,
            kind=kind,
            summary=f"{len(content)} chars",
            created_by=created_by,
        )

    def artifact_root(self, mission_id: str) -> Path:
        return self.artifacts_dir / mission_id

    def delete(self, mission_id: str) -> bool:
        import shutil

        with self._lock:
            self._hydrate()
            path = self.missions_dir / f"{mission_id}.json"
            if mission_id not in self._cache and not path.exists():
                return False
            self._cache.pop(mission_id, None)
            if path.exists():
                path.unlink()
            art = self.artifacts_dir / mission_id
            if art.exists():
                shutil.rmtree(art, ignore_errors=True)
            return True

    def _hydrate(self) -> None:
        if self._cache:
            return
        for path in self.missions_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            mission = Mission.model_validate(data)
            self._cache[mission.id] = mission
