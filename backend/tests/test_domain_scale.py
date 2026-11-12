from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.domain.blackboard import Blackboard, ingest_agent_payload
from app.domain.templates import list_templates
from app.domain.validators import normalize_payload, validate_agent_payload
from app.main import create_app


def test_templates_and_capabilities_endpoints(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SHIPCREW_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        templates = client.get("/api/templates")
        assert templates.status_code == 200
        assert len(templates.json()) >= 4
        caps = client.get("/api/capabilities")
        assert caps.status_code == 200
        body = caps.json()
        assert body["count"] >= 10
        assert "orchestration" in body["by_area"]
        metrics = client.get("/api/metrics")
        assert metrics.status_code == 200
        created = client.post(
            "/api/projects",
            json={"name": "Acme", "description": "demo", "default_template_id": "greenfield-saas"},
        )
        assert created.status_code == 200
        project_id = created.json()["id"]
        mission = client.post(
            "/api/missions",
            json={
                "title": "Portal",
                "goal": "docs portal",
                "template_id": "docs-portal",
                "project_id": project_id,
            },
        )
        assert mission.status_code == 200
        assert mission.json()["template_id"] == "docs-portal"
        project = client.get(f"/api/projects/{project_id}")
        assert mission.json()["id"] in project.json()["mission_ids"]
    get_settings.cache_clear()


def test_blackboard_and_validators():
    board = Blackboard(mission_id="m1")
    ingest_agent_payload(
        board,
        "pm",
        {"summary": "Cut scope to notes MVP", "milestones": ["api", "ui"], "risks": ["auth creep"]},
    )
    assert "pm.summary" in board.facts
    assert board.decisions
    assert board.blockers

    bad = validate_agent_payload("engineer", {"summary": "x"})
    assert any("files" in i or "short" in i for i in bad)
    good = normalize_payload("engineer", {"summary": "Implemented notes API skeleton"})
    assert isinstance(good["files"], dict)
    assert list_templates()[0].playbooks
