from __future__ import annotations

import asyncio
import io
import json
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response, StreamingResponse
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
from .domain.capabilities import capabilities_by_area, list_capabilities
from .domain.projects import Project, ProjectCreate, ProjectSummary
from .domain.templates import get_template, list_templates
from .models import Mission, MissionCreate, MissionStatus, MissionSummary
from .oauth import OAuthError, OAuthManager
from .orchestrator import Orchestrator
from .persistence.project_store import ProjectStore
from .runners import RunnerService
from .runners.types import RunnerId
from .services.event_log import EventLog
from .services.metrics import mission_metrics
from .storage import MissionStore


def create_app() -> FastAPI:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    if not data_dir.is_absolute():
        data_dir = Path(__file__).resolve().parents[1] / data_dir
    store = MissionStore(data_dir)
    projects = ProjectStore(data_dir)
    connections = ConnectionStore(data_dir)
    oauth = OAuthManager()
    runners = RunnerService()
    orchestrator = Orchestrator(store, settings, connections, runners)
    events = EventLog(data_dir)
    login_jobs: dict[str, dict[str, Any]] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = store
        app.state.projects = projects
        app.state.connections = connections
        app.state.oauth = oauth
        app.state.runners = runners
        app.state.orchestrator = orchestrator
        app.state.events = events
        app.state.settings = settings
        app.state.login_jobs = login_jobs
        yield

    app = FastAPI(title="ShipCrew", version="0.3.0", lifespan=lifespan)
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

    @app.get("/api/templates")
    def templates() -> list[dict[str, Any]]:
        return [t.model_dump(mode="json") for t in list_templates()]

    @app.get("/api/templates/{template_id}")
    def template_detail(template_id: str) -> dict[str, Any]:
        item = get_template(template_id)
        if item is None:
            raise HTTPException(404, "template not found")
        return item.model_dump(mode="json")

    @app.get("/api/metrics")
    def metrics() -> dict[str, Any]:
        return mission_metrics(store.list_missions())

    @app.get("/api/capabilities")
    def capabilities() -> dict[str, Any]:
        items = [c.model_dump(mode="json") for c in list_capabilities()]
        return {
            "count": len(items),
            "items": items,
            "by_area": {
                area: [c.model_dump(mode="json") for c in caps]
                for area, caps in capabilities_by_area().items()
            },
        }

    @app.get("/api/events")
    def list_events(limit: int = 100, mission_id: str | None = None) -> list[dict[str, Any]]:
        return events.tail(limit=min(max(limit, 1), 500), mission_id=mission_id)

    @app.get("/api/projects", response_model=list[ProjectSummary])
    def list_projects() -> list[ProjectSummary]:
        return [
            ProjectSummary(
                id=p.id,
                name=p.name,
                description=p.description,
                default_template_id=p.default_template_id,
                mission_count=len(p.mission_ids),
                updated_at=p.updated_at,
            )
            for p in projects.list()
        ]

    @app.post("/api/projects", response_model=Project)
    def create_project(body: ProjectCreate) -> Project:
        if not body.name.strip():
            raise HTTPException(400, "name required")
        if get_template(body.default_template_id) is None:
            raise HTTPException(400, "unknown template")
        project = Project(
            name=body.name.strip(),
            description=body.description.strip(),
            default_template_id=body.default_template_id,
            default_stack=body.default_stack.strip() or "Python FastAPI + React",
        )
        return projects.save(project)

    @app.get("/api/projects/{project_id}", response_model=Project)
    def get_project(project_id: str) -> Project:
        project = projects.get(project_id)
        if project is None:
            raise HTTPException(404, "project not found")
        return project

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str) -> dict[str, bool]:
        if not projects.delete(project_id):
            raise HTTPException(404, "project not found")
        return {"ok": True}

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
        items = []
        for r in runners.list_status():
            row = r.model_dump(mode="json")
            job = login_jobs.get(r.id.value)
            row["login_job"] = job
            items.append(row)
        return items

    @app.post("/api/runners/{runner_id}/login")
    async def login_runner(runner_id: str) -> dict[str, Any]:
        try:
            rid = RunnerId(runner_id)
        except ValueError as exc:
            raise HTTPException(404, "unknown runner") from exc
        existing = login_jobs.get(runner_id)
        if existing and existing.get("status") == "running":
            return {"ok": True, "started": False, "message": "login уже идёт", "job": existing}

        login_jobs[runner_id] = {"status": "running", "message": "Открыли браузерный вход…", "ok": None}

        async def _job() -> None:
            try:
                result = await runners.login(rid)
                login_jobs[runner_id] = {
                    "status": "done",
                    "ok": result.ok,
                    "message": result.message,
                }
            except Exception as exc:  # noqa: BLE001
                login_jobs[runner_id] = {"status": "done", "ok": False, "message": str(exc)}

        asyncio.create_task(_job())
        return {"ok": True, "started": True, "message": "login запущен в фоне", "job": login_jobs[runner_id]}

    @app.get("/api/runners/{runner_id}/login")
    def login_runner_status(runner_id: str) -> dict[str, Any]:
        job = login_jobs.get(runner_id)
        if job is None:
            return {"status": "idle"}
        return job

    @app.post("/api/missions", response_model=Mission)
    def create_mission(body: MissionCreate) -> Mission:
        allowed = {"llm", "codex", "claude", "cursor"}
        engineer = (body.engineer_runner or "llm").strip().lower()
        reviewer = (body.reviewer_runner or "llm").strip().lower()
        template_id = (body.template_id or "greenfield-saas").strip()
        if engineer not in allowed or reviewer not in allowed:
            raise HTTPException(400, "engineer_runner/reviewer_runner must be llm|codex|claude|cursor")
        if get_template(template_id) is None:
            raise HTTPException(400, "unknown template_id")
        if body.project_id and projects.get(body.project_id) is None:
            raise HTTPException(400, "unknown project_id")
        mission = Mission(
            title=body.title.strip(),
            goal=body.goal.strip(),
            constraints=body.constraints.strip(),
            stack_hint=body.stack_hint.strip() or "Python FastAPI + React",
            engineer_runner=engineer,
            reviewer_runner=reviewer,
            template_id=template_id,
            project_id=body.project_id,
        )
        if not mission.title or not mission.goal:
            raise HTTPException(400, "title and goal are required")
        saved = store.save(mission)
        if body.project_id:
            projects.attach_mission(body.project_id, saved.id)
        events.emit("mission_created", mission_id=saved.id, payload={"title": saved.title, "template_id": saved.template_id})
        return saved

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
        started = orchestrator.start(mission)
        events.emit("mission_started", mission_id=mission_id, payload={"status": started.status.value})
        return started

    @app.post("/api/missions/{mission_id}/cancel", response_model=Mission)
    async def cancel_mission(mission_id: str) -> Mission:
        mission = orchestrator.cancel(mission_id)
        if mission is None:
            raise HTTPException(404, "mission not found")
        return mission

    @app.delete("/api/missions/{mission_id}")
    def delete_mission(mission_id: str) -> dict[str, bool]:
        mission = store.get(mission_id)
        if mission is None:
            raise HTTPException(404, "mission not found")
        if mission.status == MissionStatus.running:
            orchestrator.cancel(mission_id)
        ok = store.delete(mission_id)
        return {"ok": ok}

    @app.get("/api/missions/{mission_id}/bundle.zip")
    def download_bundle(mission_id: str) -> Response:
        mission = store.get(mission_id)
        if mission is None:
            raise HTTPException(404, "mission not found")
        root = store.artifact_root(mission_id)
        if not root.exists():
            raise HTTPException(404, "bundle empty")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in root.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(root)).replace("\\", "/"))
        data = buf.getvalue()
        filename = f"shipcrew-{mission_id[:8]}.zip"
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

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
                        if item["type"] in {"mission_done", "mission_failed", "mission_cancelled"}:
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
        return {"path": artifact_path, "content": target.read_text(encoding="utf-8", errors="replace")}

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="ui")

    return app


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


app = create_app()
