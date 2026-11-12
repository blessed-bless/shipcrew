from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.router import build_api_router
from .config import get_settings
from .connections import ConnectionStore
from .core.logging import RequestContextMiddleware, setup_logging
from .oauth import OAuthManager
from .orchestrator import Orchestrator
from .persistence.project_store import ProjectStore
from .persistence.sqlite import SqliteIndex
from .runners import RunnerService
from .runtime.state import AppState
from .services.event_log import EventLog
from .storage import MissionStore


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    data_dir = Path(settings.data_dir)
    if not data_dir.is_absolute():
        data_dir = Path(__file__).resolve().parents[1] / data_dir

    store = MissionStore(data_dir)
    projects = ProjectStore(data_dir)
    connections = ConnectionStore(data_dir)
    oauth = OAuthManager()
    runners = RunnerService()
    events = EventLog(data_dir)
    sqlite = SqliteIndex(data_dir)
    orchestrator = Orchestrator(
        store,
        settings,
        connections,
        runners,
        events=events,
        sqlite=sqlite,
    )
    shipcrew = AppState(
        settings=settings,
        data_dir=data_dir,
        store=store,
        projects=projects,
        connections=connections,
        oauth=oauth,
        runners=runners,
        orchestrator=orchestrator,
        events=events,
        sqlite=sqlite,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        for mission in store.list_missions():
            sqlite.upsert_mission(mission)
        app.state.shipcrew = shipcrew
        # Back-compat for anything still reading flat state attrs.
        app.state.store = store
        app.state.projects = projects
        app.state.connections = connections
        app.state.oauth = oauth
        app.state.runners = runners
        app.state.orchestrator = orchestrator
        app.state.events = events
        app.state.settings = settings
        app.state.login_jobs = shipcrew.login_jobs
        app.state.sqlite = sqlite
        yield
        sqlite.close()

    app = FastAPI(title="ShipCrew", version="0.4.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    api = build_api_router()
    app.include_router(api, prefix="/api")
    app.include_router(api, prefix="/api/v1")

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="ui")

    return app
