from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_api_v1_mirrors_legacy_and_sqlite_indexes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SHIPCREW_DEMO_MODE", "true")
    monkeypatch.setenv("SHIPCREW_DATA_DIR", str(tmp_path / "data"))
    from app.config import get_settings

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        legacy = client.get("/api/health")
        v1 = client.get("/api/v1/health")
        assert legacy.status_code == 200
        assert v1.status_code == 200
        assert v1.json().get("api") == "v1"
        assert legacy.json()["ok"] is True

        created = client.post(
            "/api/v1/missions",
            json={
                "title": "Index me",
                "goal": "Check sqlite secondary index after create",
                "constraints": "",
                "template_id": "greenfield-saas",
            },
        )
        assert created.status_code == 200, created.text
        mission_id = created.json()["id"]

        indexed = client.get("/api/v1/index/missions")
        assert indexed.status_code == 200
        body = indexed.json()
        assert body["backend"] == "sqlite"
        ids = {item["id"] for item in body["items"]}
        assert mission_id in ids

        deleted = client.delete(f"/api/v1/missions/{mission_id}")
        assert deleted.status_code == 200
        after = client.get("/api/index/missions").json()
        assert mission_id not in {item["id"] for item in after["items"]}
    get_settings.cache_clear()


def test_coerce_and_validate_helpers() -> None:
    from app.domain.validators import normalize_payload, validate_agent_payload
    from app.schemas.agent_outputs import coerce_role_payload

    raw = {"summary": "short plan for mvp", "milestones": ["a"], "acceptance": ["b"]}
    normalized = normalize_payload("pm", raw)
    coerced = coerce_role_payload("pm", normalized)
    assert coerced["summary"]
    assert validate_agent_payload("pm", coerced) == []
