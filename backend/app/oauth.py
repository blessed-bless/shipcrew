from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from urllib.parse import urlencode

import httpx

from .connections import AuthMethod, ConnectionRecord, ConnectionStore, ProviderKind, catalog_entry


@dataclass
class OAuthPending:
    state: str
    provider: ProviderKind
    code_verifier: str
    callback_url: str
    frontend_redirect: str
    created_at: datetime
    model: str
    label: str


class OAuthError(RuntimeError):
    pass


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def make_pkce_pair() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


class OAuthManager:
    def __init__(self) -> None:
        self._pending: dict[str, OAuthPending] = {}
        self._lock = Lock()

    def start_openrouter(
        self,
        *,
        callback_url: str,
        frontend_redirect: str,
        model: str = "",
        label: str = "OpenRouter (browser)",
    ) -> dict[str, str]:
        verifier, challenge = make_pkce_pair()
        state = secrets.token_urlsafe(24)
        pending = OAuthPending(
            state=state,
            provider=ProviderKind.openrouter,
            code_verifier=verifier,
            callback_url=callback_url,
            frontend_redirect=frontend_redirect,
            created_at=datetime.now(timezone.utc),
            model=model or (catalog_entry("openrouter") or {}).get("default_model", ""),
            label=label,
        )
        with self._lock:
            self._pending[state] = pending
            self._purge_locked()

        query = urlencode(
            {
                "callback_url": callback_url,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
                "key_label": "ShipCrew",
            }
        )
        return {
            "provider": "openrouter",
            "state": state,
            "auth_url": f"https://openrouter.ai/auth?{query}",
        }

    def pop_pending(self, state: str) -> OAuthPending:
        with self._lock:
            self._purge_locked()
            pending = self._pending.pop(state, None)
        if pending is None:
            raise OAuthError("OAuth state не найден или просрочен. Запусти вход ещё раз.")
        return pending

    async def exchange_openrouter(self, pending: OAuthPending, code: str) -> str:
        body = {
            "code": code,
            "code_verifier": pending.code_verifier,
            "code_challenge_method": "S256",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://openrouter.ai/api/v1/auth/keys", json=body)
            if resp.status_code >= 400:
                raise OAuthError(f"OpenRouter отказал в обмене кода: {resp.status_code} {resp.text[:300]}")
            data = resp.json()
        key = data.get("key")
        if not key:
            raise OAuthError("OpenRouter не вернул key после OAuth.")
        return str(key)

    def save_openrouter_connection(
        self,
        store: ConnectionStore,
        *,
        api_key: str,
        pending: OAuthPending,
    ) -> ConnectionRecord:
        meta = catalog_entry("openrouter") or {}
        record = ConnectionRecord(
            provider=ProviderKind.openrouter,
            label=pending.label,
            auth_method=AuthMethod.oauth_browser,
            base_url=str(meta.get("default_base_url", "https://openrouter.ai/api/v1")),
            model=pending.model,
            api_key=api_key,
            active=True,
        )
        return store.upsert(record, make_active=True)

    def _purge_locked(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
        stale = [k for k, v in self._pending.items() if v.created_at < cutoff]
        for key in stale:
            del self._pending[key]
