from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.models import AgentRole, Mission
from app.runners.service import RunnerService
from app.runners.types import RunnerExecResult, RunnerId


def test_runners_endpoint(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SHIPCREW_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/runners")
        assert resp.status_code == 200
        ids = [x["id"] for x in resp.json()]
        assert ids == ["codex", "claude", "cursor"]
        for item in resp.json():
            assert "installed" in item
            assert "logged_in" in item
            assert "login_command" in item
    get_settings.cache_clear()


def test_mission_accepts_runner_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SHIPCREW_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SHIPCREW_DEMO_MODE", "true")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        created = client.post(
            "/api/missions",
            json={
                "title": "X",
                "goal": "Y",
                "engineer_runner": "codex",
                "reviewer_runner": "claude",
            },
        )
        assert created.status_code == 200
        body = created.json()
        assert body["engineer_runner"] == "codex"
        assert body["reviewer_runner"] == "claude"
    get_settings.cache_clear()


async def test_runner_service_wraps_exec(tmp_path: Path):
    service = RunnerService()
    mission = Mission(title="T", goal="G", engineer_runner="codex")
    fake = RunnerExecResult(
        ok=True,
        runner=RunnerId.codex,
        summary='{"summary":"built","files":{"a.py":"print(1)"}}',
        files_written=["a.py"],
    )
    with patch("app.runners.service.codex_runner.run", new=AsyncMock(return_value=fake)):
        payload = await service.run_role(RunnerId.codex, mission, AgentRole.engineer, tmp_path)
    assert payload["summary"] == "built"
    assert "a.py" in payload["files"]
