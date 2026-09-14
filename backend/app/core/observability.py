"""Centralized structured logging + request observability (Phase 13).

Provides:
- ``configure_logging()`` for a consistent tag-based structured format.
- ``ObservabilityMiddleware`` (FastAPI/Starlette) that logs each request with
  method, path, status, duration_ms and request id, and stamps ``x-request-id``
  on the response headers for correlation.
"""
from __future__ import annotations

import logging
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('trading.observability')


def configure_logging(level: int = logging.INFO, log_file: str | None = None) -> None:
    """Install a root handler with a consistent structured format.

    Call once from app startup. Console output is tag-based (key=value) so it
    greps cleanly; an optional rotating file handler adds durable logs.
    """
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    fmt = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    root.setLevel(level)

    if log_file:
        fh = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3, encoding='utf-8')
        fh.setFormatter(fmt)
        root.addHandler(fh)


class ObservabilityMiddleware:
    """Log every request with timing; stamp a correlation request id."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            # Pass through non-HTTP (websocket, lifespan) untouched.
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        request_id = uuid.uuid4().hex[:12]
        path = scope['path']
        method = scope.get('method', 'GET')

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers.append((b'x-request-id', request_id.encode()))
                message['headers'] = headers
                self.emit(method, path, message.get('status', 0), start, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception('unhandled exception method=%s path=%s rid=%s', method, path, request_id)
            raise

    @staticmethod
    def emit(method, path, status, start, request_id):
        duration_ms = (time.perf_counter() - start) * 1000
        msg = f'method={method} path={path} status={status} dur_ms={duration_ms:.1f} rid={request_id}'
        if status >= 500:
            logger.error(msg)
        elif status >= 400:
            logger.warning(msg)
        else:
            logger.info(msg)