from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9\-_]")
_MAX_ID_LEN = 64


def _sanitize_correlation_id(raw: str) -> str:
    """Strip non-safe chars and truncate. Returns a generated ID if nothing remains."""
    sanitized = _SAFE_ID_RE.sub("", raw)[:_MAX_ID_LEN]
    return sanitized if sanitized else f"req-{uuid.uuid4().hex[:8]}"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        clear_contextvars()

        incoming = request.headers.get("x-request-id")
        if incoming:
            correlation_id = _sanitize_correlation_id(incoming)
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(elapsed_ms)

        return response
