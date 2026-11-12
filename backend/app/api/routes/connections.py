from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from ...connections import (
    PROVIDER_CATALOG,
    AuthMethod,
    ConnectionCreate,
    ConnectionPublic,
    ConnectionRecord,
    ProviderKind,
    catalog_entry,
)
from ...oauth import OAuthError
from ...runtime.state import AppState
from ..deps import get_state

router = APIRouter(tags=["connections"])


@router.get("/providers")
def providers() -> list[dict[str, Any]]:
    return PROVIDER_CATALOG


@router.get("/connections", response_model=list[ConnectionPublic])
def list_connections(app: AppState = Depends(get_state)) -> list[ConnectionPublic]:
    return app.connections.list_public()


@router.post("/connections", response_model=ConnectionPublic)
def create_connection(body: ConnectionCreate, app: AppState = Depends(get_state)) -> ConnectionPublic:
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
    saved = app.connections.upsert(record, make_active=body.make_active)
    app.orchestrator.refresh_llm()
    return saved.public()


@router.post("/connections/{connection_id}/activate", response_model=ConnectionPublic)
def activate_connection(connection_id: str, app: AppState = Depends(get_state)) -> ConnectionPublic:
    try:
        saved = app.connections.set_active(connection_id)
    except KeyError as exc:
        raise HTTPException(404, "connection not found") from exc
    app.orchestrator.refresh_llm()
    return saved.public()


@router.delete("/connections/{connection_id}")
def delete_connection(connection_id: str, app: AppState = Depends(get_state)) -> dict[str, bool]:
    try:
        app.connections.delete(connection_id)
    except KeyError as exc:
        raise HTTPException(404, "connection not found") from exc
    app.orchestrator.refresh_llm()
    return {"ok": True}


@router.post("/connections/oauth/openrouter/start")
def start_openrouter_oauth(request: Request, app: AppState = Depends(get_state)) -> dict[str, str]:
    callback_url = f"{app.settings.public_base_url.rstrip('/')}/api/connections/oauth/openrouter/callback"
    frontend = app.settings.frontend_url.rstrip("/")
    referer = request.headers.get("referer")
    if referer and "127.0.0.1:8787" in referer:
        frontend = app.settings.public_base_url.rstrip("/")
    return app.oauth.start_openrouter(callback_url=callback_url, frontend_redirect=frontend)


@router.get("/connections/oauth/openrouter/callback")
async def openrouter_oauth_callback(request: Request, app: AppState = Depends(get_state)):
    code = request.query_params.get("code")
    oauth_state = request.query_params.get("state")
    error = request.query_params.get("error")
    frontend = app.settings.frontend_url.rstrip("/")
    if error:
        return RedirectResponse(f"{frontend}/?oauth=error&reason={error}")
    if not code or not oauth_state:
        return RedirectResponse(f"{frontend}/?oauth=error&reason=missing_code")
    try:
        pending = app.oauth.pop_pending(oauth_state)
        frontend = pending.frontend_redirect.rstrip("/")
        key = await app.oauth.exchange_openrouter(pending, code)
        app.oauth.save_openrouter_connection(app.connections, api_key=key, pending=pending)
        app.orchestrator.refresh_llm()
        return RedirectResponse(f"{frontend}/?oauth=ok&provider=openrouter")
    except OAuthError as exc:
        q = urlencode({"oauth": "error", "reason": str(exc)})
        return RedirectResponse(f"{frontend}/?{q}")
