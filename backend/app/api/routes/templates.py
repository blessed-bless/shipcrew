from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...domain.templates import get_template, list_templates

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
def templates() -> list[dict[str, Any]]:
    return [t.model_dump(mode="json") for t in list_templates()]


@router.get("/{template_id}")
def template_detail(template_id: str) -> dict[str, Any]:
    item = get_template(template_id)
    if item is None:
        raise HTTPException(404, "template not found")
    return item.model_dump(mode="json")
