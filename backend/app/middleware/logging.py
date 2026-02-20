"""ASGI middleware for structured request logging."""

import time
from uuid import uuid4

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

logger = structlog.get_logger()

SKIP_PATHS = {"/health", "/api/health"}


class RequestLoggingMiddleware:
    """Log method, path, status_code, and duration_ms for each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex[:8]
        method = scope.get("method", "")
        status_code = 0
        start = time.monotonic()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            logger.info(
                "request",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            structlog.contextvars.clear_contextvars()
