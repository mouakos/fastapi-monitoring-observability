"""Correlation ID setup using the asgi_correlation_id package.

asgi_correlation_id automatically generates a unique ID for every incoming request,
stores it in a ContextVar (correlation_id), and exposes it via the X-Request-ID
response header. This module wires that ID into Loguru so every log record emitted
during a request is automatically tagged with the same ID.
"""

from typing import Any

from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI

from app.logging import register_log_patcher

# ---------------------------------------------------------------------------
# Log patcher — reads correlation_id ContextVar and stamps every Loguru record
# ---------------------------------------------------------------------------


def _inject_correlation_id(record: dict[str, Any]) -> None:
    """Stamp the active correlation ID onto a Loguru log record.

    Called by the Loguru patcher registry on every log record. Reads the
    correlation_id ContextVar set by CorrelationIdMiddleware and writes it into
    record["extra"]["request_id"] so it appears consistently in all log sinks.

    Args:
        record: The Loguru log record to modify.
    """
    request_id = correlation_id.get()
    if request_id:
        record["extra"]["request_id"] = request_id


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def setup_correlation_id(app: FastAPI) -> None:
    """Register CorrelationIdMiddleware and wire the correlation ID into Loguru.

    CorrelationIdMiddleware (from asgi_correlation_id) generates or inherits a
    unique ID per request, stores it in the correlation_id ContextVar, and exposes
    it via the X-Request-ID response header. Registering the Loguru patcher here
    ensures the ID is present in every log record for the lifetime of the request.

    Args:
        app: The FastAPI application instance to add the middleware to.
    """
    app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")
    register_log_patcher(_inject_correlation_id)
