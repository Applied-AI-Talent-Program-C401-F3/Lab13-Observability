from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9\-_]")
_MAX_ID_LEN = 64
_INCOMING_ID_HEADERS = ("x-request-id", "x-correlation-id")


def _sanitize_correlation_id(raw: str) -> str:
    """Strip non-safe chars and truncate. Returns a generated ID if nothing remains."""
    sanitized = _SAFE_ID_RE.sub("", raw)[:_MAX_ID_LEN]
    return sanitized if sanitized else f"req-{uuid.uuid4().hex[:8]}"


def _extract_incoming_correlation_id(request: Request) -> str | None:
    for header in _INCOMING_ID_HEADERS:
        candidate = request.headers.get(header)
        if candidate:
            return candidate
    return None


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        clear_contextvars()

        incoming = _extract_incoming_correlation_id(request)
        if incoming:
            correlation_id = _sanitize_correlation_id(incoming)
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            response.headers["x-request-id"] = correlation_id
            response.headers["x-correlation-id"] = correlation_id
            response.headers["x-response-time-ms"] = str(elapsed_ms)

            return response
        finally:
            clear_contextvars()
