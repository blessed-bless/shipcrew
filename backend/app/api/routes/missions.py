from __future__ import annotations

import asyncio
import io
import json
import zipfile
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from ...domain.templates import get_template
from ...models import Mission, MissionCreate, MissionStatus, MissionSummary
from ...runtime.state import AppState
from ..deps import get_state

router = APIRouter(prefix="/missions", tags=["missions"])


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("", response_model=list[MissionSummary])
def list_missions(app: AppState = Depends(get_state)) -> list[MissionSummary]:
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
        for m in app.store.list_missions()
    ]


@router.post("", response_model=Mission)
def create_mission(body: MissionCreate, app: AppState = Depends(get_state)) -> Mission:
    allowed = {"llm", "codex", "claude", "cursor"}
    engineer = (body.engineer_runner or "llm").strip().lower()
    reviewer = (body.reviewer_runner or "llm").strip().lower()
    template_id = (body.template_id or "greenfield-saas").strip()
    if engineer not in allowed or reviewer not in allowed:
        raise HTTPException(400, "engineer_runner/reviewer_runner must be llm|codex|claude|cursor")
    if get_template(template_id) is None:
        raise HTTPException(400, "unknown template_id")
    if body.project_id and app.projects.get(body.project_id) is None:
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
    saved = app.store.save(mission)
    if body.project_id:
        app.projects.attach_mission(body.project_id, saved.id)
    app.events.emit(
        "mission_created",
        mission_id=saved.id,
        payload={"title": saved.title, "template_id": saved.template_id},
    )
    if app.sqlite is not None:
        app.sqlite.upsert_mission(saved)
    return saved


@router.get("/{mission_id}", response_model=Mission)
def get_mission(mission_id: str, app: AppState = Depends(get_state)) -> Mission:
    mission = app.store.get(mission_id)
    if mission is None:
        raise HTTPException(404, "mission not found")
    return mission


@router.post("/{mission_id}/run", response_model=Mission)
async def run_mission(mission_id: str, app: AppState = Depends(get_state)) -> Mission:
    mission = app.store.get(mission_id)
    if mission is None:
        raise HTTPException(404, "mission not found")
    if mission.status == MissionStatus.running:
        return mission
    started = app.orchestrator.start(mission)
    app.events.emit("mission_started", mission_id=mission_id, payload={"status": started.status.value})
    if app.sqlite is not None:
        app.sqlite.upsert_mission(started)
    return started


@router.post("/{mission_id}/cancel", response_model=Mission)
async def cancel_mission(mission_id: str, app: AppState = Depends(get_state)) -> Mission:
    mission = app.orchestrator.cancel(mission_id)
    if mission is None:
        raise HTTPException(404, "mission not found")
    if app.sqlite is not None:
        app.sqlite.upsert_mission(mission)
    return mission


@router.delete("/{mission_id}")
def delete_mission(mission_id: str, app: AppState = Depends(get_state)) -> dict[str, bool]:
    mission = app.store.get(mission_id)
    if mission is None:
        raise HTTPException(404, "mission not found")
    if mission.status == MissionStatus.running:
        app.orchestrator.cancel(mission_id)
    ok = app.store.delete(mission_id)
    if ok and app.sqlite is not None:
        app.sqlite.delete_mission(mission_id)
    return {"ok": ok}


@router.get("/{mission_id}/bundle.zip")
def download_bundle(mission_id: str, app: AppState = Depends(get_state)) -> Response:
    mission = app.store.get(mission_id)
    if mission is None:
        raise HTTPException(404, "mission not found")
    root = app.store.artifact_root(mission_id)
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


@router.get("/{mission_id}/events")
async def mission_events(
    mission_id: str,
    request: Request,
    app: AppState = Depends(get_state),
) -> StreamingResponse:
    mission = app.store.get(mission_id)
    if mission is None:
        raise HTTPException(404, "mission not found")

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def on_event(event_type: str, payload: dict[str, Any]) -> None:
        await queue.put({"type": event_type, "payload": payload})

    app.orchestrator.subscribe(mission_id, on_event)

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
            app.orchestrator.unsubscribe(mission_id, on_event)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/{mission_id}/artifacts/{artifact_path:path}")
def read_artifact(mission_id: str, artifact_path: str, app: AppState = Depends(get_state)) -> dict[str, str]:
    mission = app.store.get(mission_id)
    if mission is None:
        raise HTTPException(404, "mission not found")
    root = app.store.artifact_root(mission_id).resolve()
    target = (root / artifact_path).resolve()
    if not str(target).startswith(str(root)) or not target.exists():
        raise HTTPException(404, "artifact not found")
    return {"path": artifact_path, "content": target.read_text(encoding="utf-8", errors="replace")}
