from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ...runners.types import RunnerId
from ...runtime.state import AppState
from ..deps import get_state

router = APIRouter(prefix="/runners", tags=["runners"])


@router.get("")
def list_runners(app: AppState = Depends(get_state)) -> list[dict[str, Any]]:
    items = []
    for r in app.runners.list_status():
        row = r.model_dump(mode="json")
        job = app.login_jobs.get(r.id.value)
        row["login_job"] = job
        items.append(row)
    return items


@router.post("/{runner_id}/login")
async def login_runner(runner_id: str, app: AppState = Depends(get_state)) -> dict[str, Any]:
    try:
        rid = RunnerId(runner_id)
    except ValueError as exc:
        raise HTTPException(404, "unknown runner") from exc
    existing = app.login_jobs.get(runner_id)
    if existing and existing.get("status") == "running":
        return {"ok": True, "started": False, "message": "login уже идёт", "job": existing}

    app.login_jobs[runner_id] = {
        "status": "running",
        "message": "Открыли браузерный вход…",
        "ok": None,
    }

    async def _job() -> None:
        try:
            result = await app.runners.login(rid)
            app.login_jobs[runner_id] = {
                "status": "done",
                "ok": result.ok,
                "message": result.message,
            }
        except Exception as exc:  # noqa: BLE001
            app.login_jobs[runner_id] = {"status": "done", "ok": False, "message": str(exc)}

    asyncio.create_task(_job())
    return {
        "ok": True,
        "started": True,
        "message": "login запущен в фоне",
        "job": app.login_jobs[runner_id],
    }


@router.get("/{runner_id}/login")
def login_runner_status(runner_id: str, app: AppState = Depends(get_state)) -> dict[str, Any]:
    job = app.login_jobs.get(runner_id)
    if job is None:
        return {"status": "idle"}
    return job
