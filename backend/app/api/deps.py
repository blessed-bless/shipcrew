from __future__ import annotations

from fastapi import Request

from ..runtime.state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.shipcrew
