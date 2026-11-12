from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.oauth import make_pkce_pair


def test_pkce_challenge_stable_shape():
    verifier, challenge = make_pkce_pair()
    assert len(verifier) >= 32
    assert len(challenge) >= 32
    assert "=" not in verifier
    assert "=" not in challenge


def test_providers_and_openrouter_start(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SHIPCREW_DEMO_MODE", "true")
    monkeypatch.setenv("SHIPCREW_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SHIPCREW_PUBLIC_BASE_URL", "http://127.0.0.1:8787")
    monkeypatch.setenv("SHIPCREW_FRONTEND_URL", "http://127.0.0.1:5173")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        providers = client.get("/api/providers")
        assert providers.status_code == 200
        ids = [p["id"] for p in providers.json()]
        assert "openrouter" in ids
        assert "anthropic" in ids

        started = client.post("/api/connections/oauth/openrouter/start")
        assert started.status_code == 200
        body = started.json()
        assert "auth_url" in body
        parsed = urlparse(body["auth_url"])
        assert parsed.netloc == "openrouter.ai"
        qs = parse_qs(parsed.query)
        assert qs["code_challenge_method"] == ["S256"]
        assert "code_challenge" in qs
        assert "state" in qs
        assert qs["callback_url"][0].endswith("/api/connections/oauth/openrouter/callback")

        created = client.post(
            "/api/connections",
            json={
                "provider": "openai",
                "api_key": "sk-test-1234567890",
                "model": "gpt-4o-mini",
                "make_active": True,
            },
        )
        assert created.status_code == 200
        assert created.json()["active"] is True
        assert created.json()["auth_method"] == "api_key"

        listed = client.get("/api/connections")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        blocked = client.post(
            "/api/connections",
            json={"provider": "anthropic", "api_key": "", "make_active": True},
        )
        assert blocked.status_code == 400
    get_settings.cache_clear()
