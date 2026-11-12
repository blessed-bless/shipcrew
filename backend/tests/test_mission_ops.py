import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def _client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SHIPCREW_DEMO_MODE", "true")
    monkeypatch.setenv("SHIPCREW_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_cancel_and_bundle_zip(tmp_path: Path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        created = client.post(
            "/api/missions",
            json={"title": "Zip Me", "goal": "bundle artifacts", "engineer_runner": "llm"},
        )
        assert created.status_code == 200
        mission_id = created.json()["id"]

        started = client.post(f"/api/missions/{mission_id}/run")
        assert started.status_code == 200

        # wait finish in demo
        body = None
        for _ in range(80):
            body = client.get(f"/api/missions/{mission_id}").json()
            if body["status"] in {"done", "failed", "cancelled"}:
                break
            import time

            time.sleep(0.05)
        assert body["status"] == "done"

        z = client.get(f"/api/missions/{mission_id}/bundle.zip")
        assert z.status_code == 200
        assert z.headers["content-type"].startswith("application/zip")
        with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
            names = zf.namelist()
            assert names

        deleted = client.delete(f"/api/missions/{mission_id}")
        assert deleted.status_code == 200
        assert client.get(f"/api/missions/{mission_id}").status_code == 404
    get_settings.cache_clear()


def test_async_runner_login_starts(tmp_path: Path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        # Even if binary missing, endpoint should accept and finish job.
        resp = client.post("/api/runners/codex/login")
        assert resp.status_code == 200
        assert resp.json()["started"] in {True, False}
        status = client.get("/api/runners/codex/login")
        assert status.status_code == 200
        assert "status" in status.json()
    get_settings.cache_clear()
