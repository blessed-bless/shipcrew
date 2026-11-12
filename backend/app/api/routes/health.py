from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from ...domain.capabilities import capabilities_by_area, list_capabilities
from ...services.metrics import mission_metrics
from ..deps import get_state
from ...runtime.state import AppState

router = APIRouter(tags=["system"])


@router.get("/health")
def health(state: AppState = Depends(get_state)) -> dict[str, Any]:
    active = state.connections.get_active()
    return {
        "ok": True,
        "demo_mode": state.orchestrator.llm.demo,
        "model": active.model if active else state.settings.llm_model,
        "active_provider": active.provider.value if active else None,
        "active_auth": active.auth_method.value if active else None,
        "api": "v1",
    }


@router.get("/crew")
def crew() -> list[dict[str, str]]:
    from ...agents import AGENTS, PIPELINE

    return [{"role": role.value, "title": AGENTS[role].title} for role in PIPELINE]


@router.get("/metrics")
def metrics(state: AppState = Depends(get_state)) -> dict[str, Any]:
    return mission_metrics(state.store.list_missions())


@router.get("/capabilities")
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


@router.get("/events")
def list_events(
    limit: int = Query(100, ge=1, le=500),
    mission_id: str | None = None,
    state: AppState = Depends(get_state),
) -> list[dict[str, Any]]:
    return state.events.tail(limit=limit, mission_id=mission_id)
