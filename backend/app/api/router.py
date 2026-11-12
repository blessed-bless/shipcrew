from __future__ import annotations

from fastapi import APIRouter

from .routes import connections, health, index, missions, projects, runners, templates


def build_api_router() -> APIRouter:
    api = APIRouter()
    api.include_router(health.router)
    api.include_router(templates.router)
    api.include_router(projects.router)
    api.include_router(connections.router)
    api.include_router(runners.router)
    api.include_router(missions.router)
    api.include_router(index.router)
    return api
