"""Middleware to record custom OpenTelemetry metrics for FastAPI requests."""

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.custom_metrics import (
    HTTP_REQUEST_COUNTER,
    HTTP_REQUEST_DURATION_MS,
    HTTP_REQUEST_IN_PROGRESS,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to record custom OpenTelemetry metrics for FastAPI requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware to record custom OpenTelemetry metrics for FastAPI requests.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable[[Request], Awaitable[Response]]): The next handler in the middleware chain.

        Returns:
            Response: The HTTP response from the next handler.
        """
        attrs = {
            "http.method": request.method,
            "http.path": request.url.path,
        }
        # Increment in-progress counter
        HTTP_REQUEST_IN_PROGRESS.add(1, attributes=attrs)
        start_time = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Decrement in-progress counter (same label set as the increment)
            HTTP_REQUEST_IN_PROGRESS.add(-1, attributes=attrs)

            attrs.update({"http.status_code": str(status_code)})
            # Record request count and duration
            HTTP_REQUEST_DURATION_MS.record(duration_ms, attributes=attrs)
            # Increment request count
            HTTP_REQUEST_COUNTER.add(1, attributes=attrs)
