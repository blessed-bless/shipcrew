import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import Mission, MissionStatus
from app.orchestrator import Orchestrator
from app.storage import MissionStore


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SHIPCREW_DEMO_MODE", "true")
    monkeypatch.setenv("SHIPCREW_DATA_DIR", str(tmp_path / "data"))
    from app.config import get_settings

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_health(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["demo_mode"] is True


def test_crew_roster(client: TestClient):
    resp = client.get("/api/crew")
    assert resp.status_code == 200
    roles = [x["role"] for x in resp.json()]
    assert roles == ["pm", "architect", "engineer", "reviewer", "devops"]


def test_mission_pipeline_to_done(tmp_path: Path):
    settings = Settings(demo_mode=True, data_dir=tmp_path / "data", llm_api_key="")
    store = MissionStore(settings.data_dir)
    orch = Orchestrator(store, settings)
    mission = store.save(
        Mission(
            title="Task Board",
            goal="Build a tiny task board API with health check",
            stack_hint="Python FastAPI + React",
        )
    )

    async def wait_done():
        orch.start(mission)
        for _ in range(100):
            current = store.get(mission.id)
            assert current is not None
            if current.status in {MissionStatus.done, MissionStatus.failed}:
                return current
            await asyncio.sleep(0.05)
        raise AssertionError("mission did not finish")

    finished = asyncio.run(wait_done())
    assert finished.status == MissionStatus.done
    assert finished.ship_bundle
    assert len(finished.messages) >= 5
    assert any(a.kind == "infra" for a in finished.artifacts)
    assert (Path(finished.ship_bundle)).exists()


def test_create_and_run_via_api(client: TestClient):
    created = client.post(
        "/api/missions",
        json={
            "title": "Notes API",
            "goal": "CRUD notes service ready for docker",
            "constraints": "No auth in MVP",
        },
    )
    assert created.status_code == 200
    mission_id = created.json()["id"]

    started = client.post(f"/api/missions/{mission_id}/run")
    assert started.status_code == 200

    for _ in range(80):
        got = client.get(f"/api/missions/{mission_id}")
        assert got.status_code == 200
        body = got.json()
        if body["status"] in {"done", "failed"}:
            break
        import time

        time.sleep(0.05)
    else:
        raise AssertionError("timeout waiting for mission")

    assert body["status"] == "done"
    assert len(body["messages"]) >= 5
    assert body["ship_bundle"]
