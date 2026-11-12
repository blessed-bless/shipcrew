from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .connections import (
    PROVIDER_CATALOG,
    AuthMethod,
    ConnectionCreate,
    ConnectionPublic,
    ConnectionRecord,
    ConnectionStore,
    ProviderKind,
    catalog_entry,
)
from .models import Mission, MissionCreate, MissionStatus, MissionSummary
from .oauth import OAuthError, OAuthManager
from .orchestrator import Orchestrator
from .runners import RunnerService
from .runners.types import RunnerId
from .storage import MissionStore


def create_app() -> FastAPI:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    if not data_dir.is_absolute():
        data_dir = Path(__file__).resolve().parents[1] / data_dir
    store = MissionStore(data_dir)
    connections = ConnectionStore(data_dir)
    oauth = OAuthManager()
    runners = RunnerService()
    orchestrator = Orchestrator(store, settings, connections, runners)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = store
        app.state.connections = connections
        app.state.oauth = oauth
        app.state.runners = runners
        app.state.orchestrator = orchestrator
        app.state.settings = settings
        yield

    app = FastAPI(title="ShipCrew", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        active = connections.get_active()
        return {
            "ok": True,
            "demo_mode": orchestrator.llm.demo,
            "model": active.model if active else settings.llm_model,
            "active_provider": active.provider.value if active else None,
            "active_auth": active.auth_method.value if active else None,
        }

    @app.get("/api/crew")
    def crew() -> list[dict[str, str]]:
        from .agents import AGENTS, PIPELINE

        return [{"role": role.value, "title": AGENTS[role].title} for role in PIPELINE]

    @app.get("/api/providers")
    def providers() -> list[dict[str, Any]]:
        return PROVIDER_CATALOG

    @app.get("/api/connections", response_model=list[ConnectionPublic])
    def list_connections() -> list[ConnectionPublic]:
        return connections.list_public()

    @app.post("/api/connections", response_model=ConnectionPublic)
    def create_connection(body: ConnectionCreate) -> ConnectionPublic:
        meta = catalog_entry(body.provider.value)
        if meta is None:
            raise HTTPException(400, "unknown provider")

        if body.provider == ProviderKind.anthropic and not body.api_key.strip():
            raise HTTPException(
                400,
                meta.get("blocked_oauth_reason")
                or "Для Anthropic нужен API-ключ из Claude Console. OAuth Claude Code недоступен сторонним приложениям.",
            )

        if body.provider != ProviderKind.ollama and not body.api_key.strip():
            raise HTTPException(400, "api_key обязателен для этого провайдера")

        auth_method = AuthMethod.local if body.provider == ProviderKind.ollama else AuthMethod.api_key
        record = ConnectionRecord(
            provider=body.provider,
            label=body.label.strip() or str(meta["name"]),
            auth_method=auth_method,
            base_url=(body.base_url.strip() or str(meta["default_base_url"])),
            model=(body.model.strip() or str(meta["default_model"])),
            api_key=body.api_key.strip(),
        )
        saved = connections.upsert(record, make_active=body.make_active)
        orchestrator.refresh_llm()
        return saved.public()

    @app.post("/api/connections/{connection_id}/activate", response_model=ConnectionPublic)
    def activate_connection(connection_id: str) -> ConnectionPublic:
        try:
            saved = connections.set_active(connection_id)
        except KeyError as exc:
            raise HTTPException(404, "connection not found") from exc
        orchestrator.refresh_llm()
        return saved.public()

    @app.delete("/api/connections/{connection_id}")
    def delete_connection(connection_id: str) -> dict[str, bool]:
        try:
            connections.delete(connection_id)
        except KeyError as exc:
            raise HTTPException(404, "connection not found") from exc
        orchestrator.refresh_llm()
        return {"ok": True}

    @app.post("/api/connections/oauth/openrouter/start")
    def start_openrouter_oauth(request: Request) -> dict[str, str]:
        # callback обязан быть на бэкенде — туда OpenRouter вернёт ?code=
        callback_url = f"{settings.public_base_url.rstrip('/')}/api/connections/oauth/openrouter/callback"
        # после успеха уводим пользователя обратно в UI
        frontend = settings.frontend_url.rstrip("/")
        # если UI открыт с того же origin (prod static), вернём на /
        referer = request.headers.get("referer")
        if referer and "127.0.0.1:8787" in referer:
            frontend = settings.public_base_url.rstrip("/")
        started = oauth.start_openrouter(callback_url=callback_url, frontend_redirect=frontend)
        return started

    @app.get("/api/connections/oauth/openrouter/callback")
    async def openrouter_oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None):
        frontend = settings.frontend_url.rstrip("/")
        if error:
            return RedirectResponse(f"{frontend}/?oauth=error&reason={error}")
        if not code or not state:
            return RedirectResponse(f"{frontend}/?oauth=error&reason=missing_code")
        try:
            pending = oauth.pop_pending(state)
            frontend = pending.frontend_redirect.rstrip("/")
            key = await oauth.exchange_openrouter(pending, code)
            oauth.save_openrouter_connection(connections, api_key=key, pending=pending)
            orchestrator.refresh_llm()
            return RedirectResponse(f"{frontend}/?oauth=ok&provider=openrouter")
        except OAuthError as exc:
            q = urlencode({"oauth": "error", "reason": str(exc)})
            return RedirectResponse(f"{frontend}/?{q}")

    @app.get("/api/missions", response_model=list[MissionSummary])
    def list_missions() -> list[MissionSummary]:
        return [
            MissionSummary(
                id=m.id,
                title=m.title,
                status=m.status,
                current_role=m.current_role,
                artifact_count=len(m.artifacts),
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in store.list_missions()
        ]

    @app.get("/api/runners")
    def list_runners() -> list[dict[str, Any]]:
        return [r.model_dump(mode="json") for r in runners.list_status()]

    @app.post("/api/runners/{runner_id}/login")
    async def login_runner(runner_id: str) -> dict[str, Any]:
        try:
            rid = RunnerId(runner_id)
        except ValueError as exc:
            raise HTTPException(404, "unknown runner") from exc
        result = await runners.login(rid)
        return result.model_dump(mode="json")

    @app.post("/api/missions", response_model=Mission)
    def create_mission(body: MissionCreate) -> Mission:
        allowed = {"llm", "codex", "claude", "cursor"}
        engineer = (body.engineer_runner or "llm").strip().lower()
        reviewer = (body.reviewer_runner or "llm").strip().lower()
        if engineer not in allowed or reviewer not in allowed:
            raise HTTPException(400, "engineer_runner/reviewer_runner must be llm|codex|claude|cursor")
        mission = Mission(
            title=body.title.strip(),
            goal=body.goal.strip(),
            constraints=body.constraints.strip(),
            stack_hint=body.stack_hint.strip() or "Python FastAPI + React",
            engineer_runner=engineer,
            reviewer_runner=reviewer,
        )
        if not mission.title or not mission.goal:
            raise HTTPException(400, "title and goal are required")
        return store.save(mission)

    @app.get("/api/missions/{mission_id}", response_model=Mission)
    def get_mission(mission_id: str) -> Mission:
        mission = store.get(mission_id)
        if mission is None:
            raise HTTPException(404, "mission not found")
        return mission

    @app.post("/api/missions/{mission_id}/run", response_model=Mission)
    async def run_mission(mission_id: str) -> Mission:
        mission = store.get(mission_id)
        if mission is None:
            raise HTTPException(404, "mission not found")
        if mission.status == MissionStatus.running:
            return mission
        return orchestrator.start(mission)

    @app.get("/api/missions/{mission_id}/events")
    async def mission_events(mission_id: str, request: Request) -> StreamingResponse:
        mission = store.get(mission_id)
        if mission is None:
            raise HTTPException(404, "mission not found")

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def on_event(event_type: str, payload: dict[str, Any]) -> None:
            await queue.put({"type": event_type, "payload": payload})

        orchestrator.subscribe(mission_id, on_event)

        async def gen():
            try:
                yield _sse({"type": "snapshot", "payload": json.loads(mission.model_dump_json())})
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=15.0)
                        yield _sse(item)
                        if item["type"] in {"mission_done", "mission_failed"}:
                            break
                    except asyncio.TimeoutError:
                        yield _sse({"type": "ping", "payload": {}})
            finally:
                orchestrator.unsubscribe(mission_id, on_event)

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/missions/{mission_id}/artifacts/{artifact_path:path}")
    def read_artifact(mission_id: str, artifact_path: str) -> dict[str, str]:
        mission = store.get(mission_id)
        if mission is None:
            raise HTTPException(404, "mission not found")
        root = store.artifact_root(mission_id).resolve()
        target = (root / artifact_path).resolve()
        if not str(target).startswith(str(root)) or not target.exists():
            raise HTTPException(404, "artifact not found")
        return {"path": artifact_path, "content": target.read_text(encoding="utf-8")}

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="ui")

    return app


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


app = create_app()
