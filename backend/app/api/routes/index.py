from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from ...runtime.state import AppState
from ..deps import get_state

router = APIRouter(prefix="/index", tags=["index"])


@router.get("/missions")
def indexed_missions(
    limit: int = Query(100, ge=1, le=500),
    app: AppState = Depends(get_state),
) -> dict[str, Any]:
    if app.sqlite is None:
        return {"items": [], "by_status": {}, "backend": "none"}
    return {
        "items": app.sqlite.list_summaries(limit=limit),
        "by_status": app.sqlite.count_by_status(),
        "backend": "sqlite",
    }
