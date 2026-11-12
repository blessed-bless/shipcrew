from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            status = response.status_code if response is not None else 500
            logging.getLogger("shipcrew.http").info(
                "%s %s -> %s (%.1fms) rid=%s",
                request.method,
                request.url.path,
                status,
                elapsed_ms,
                request_id,
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
