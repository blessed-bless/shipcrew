from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class AuthMethod(str, Enum):
    oauth_browser = "oauth_browser"
    api_key = "api_key"
    local = "local"


class ProviderKind(str, Enum):
    openrouter = "openrouter"
    openai = "openai"
    anthropic = "anthropic"
    ollama = "ollama"


PROVIDER_CATALOG: list[dict[str, Any]] = [
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "auth_methods": ["oauth_browser", "api_key"],
        "oauth_label": "Войти через OpenRouter",
        "description": "Браузерный вход: кредиты/подписка на стороне OpenRouter. Claude, GPT и другие модели через один аккаунт.",
        "default_base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-3.5-sonnet",
        "supports_oauth": True,
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "auth_methods": ["api_key"],
        "oauth_label": None,
        "description": "Официальный API-ключ. ChatGPT Plus ≠ API — нужен ключ из platform.openai.com.",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "supports_oauth": False,
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "auth_methods": ["api_key"],
        "oauth_label": None,
        "description": "Только API-ключ из Claude Console. Вход через Claude.ai / Claude Code в сторонние приложения Anthropic запрещает.",
        "default_base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-latest",
        "supports_oauth": False,
        "blocked_oauth_reason": (
            "Anthropic разрешает subscription OAuth только в своих приложениях "
            "(Claude.ai, Claude Code). Для ShipCrew — Console API key или OpenRouter."
        ),
    },
    {
        "id": "ollama",
        "name": "Ollama (локально)",
        "auth_methods": ["local"],
        "oauth_label": None,
        "description": "Локальные модели без облачного входа.",
        "default_base_url": "http://127.0.0.1:11434/v1",
        "default_model": "llama3.2",
        "supports_oauth": False,
    },
]


class ConnectionCreate(BaseModel):
    provider: ProviderKind
    label: str = ""
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    make_active: bool = True


class ConnectionPublic(BaseModel):
    id: str
    provider: ProviderKind
    label: str
    auth_method: AuthMethod
    base_url: str
    model: str
    key_preview: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ConnectionRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    provider: ProviderKind
    label: str = ""
    auth_method: AuthMethod
    base_url: str
    model: str
    api_key: str = ""
    active: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def public(self) -> ConnectionPublic:
        key = self.api_key or ""
        if len(key) <= 8:
            preview = "••••" if key else "нет ключа"
        else:
            preview = f"{key[:4]}…{key[-4:]}"
        return ConnectionPublic(
            id=self.id,
            provider=self.provider,
            label=self.label or self.provider.value,
            auth_method=self.auth_method,
            base_url=self.base_url,
            model=self.model,
            key_preview=preview,
            active=self.active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ConnectionStore:
    def __init__(self, root: Path) -> None:
        self.path = root / "connections.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._items: dict[str, ConnectionRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw.get("connections", []):
            rec = ConnectionRecord.model_validate(item)
            self._items[rec.id] = rec

    def _persist(self) -> None:
        payload = {"connections": [c.model_dump(mode="json") for c in self._items.values()]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_public(self) -> list[ConnectionPublic]:
        with self._lock:
            return [
                c.public()
                for c in sorted(self._items.values(), key=lambda x: x.created_at, reverse=True)
            ]

    def get(self, connection_id: str) -> ConnectionRecord | None:
        with self._lock:
            return self._items.get(connection_id)

    def get_active(self) -> ConnectionRecord | None:
        with self._lock:
            for item in self._items.values():
                if item.active:
                    return item
            return None

    def upsert(self, record: ConnectionRecord, *, make_active: bool = False) -> ConnectionRecord:
        with self._lock:
            record.updated_at = utc_now()
            if make_active or record.active:
                for other in self._items.values():
                    other.active = False
                record.active = True
            self._items[record.id] = record
            self._persist()
            return record

    def set_active(self, connection_id: str) -> ConnectionRecord:
        with self._lock:
            if connection_id not in self._items:
                raise KeyError(connection_id)
            for item in self._items.values():
                item.active = item.id == connection_id
                item.updated_at = utc_now()
            self._persist()
            return self._items[connection_id]

    def delete(self, connection_id: str) -> None:
        with self._lock:
            if connection_id not in self._items:
                raise KeyError(connection_id)
            del self._items[connection_id]
            self._persist()


def catalog_entry(provider: str) -> dict[str, Any] | None:
    for item in PROVIDER_CATALOG:
        if item["id"] == provider:
            return item
    return None
