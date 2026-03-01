"""Middleware to record custom OpenTelemetry metrics for FastAPI requests."""

import time
from collections.abc import Awaitable, Callable

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, UpDownCounter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.settings import config
from app.utils import get_request_info


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to record custom OpenTelemetry metrics for FastAPI requests."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialise the middleware and create OTEL metric instruments.

        Instruments are created here (after MeterProvider is set by setup_otlp)
        rather than at module level to ensure they use the real exporter.
        """
        super().__init__(app)
        meter = metrics.get_meter(f"{config.otel_service_name}.metrics")
        self._counter: Counter = meter.create_counter(
            name="http_request_count",
            description="Count of HTTP requests received",
        )
        self._duration: Histogram = meter.create_histogram(
            name="http_request_duration_ms",
            description="Duration of HTTP requests in milliseconds",
        )
        self._in_progress: UpDownCounter = meter.create_up_down_counter(
            name="http_request_in_progress",
            description="Number of HTTP requests currently in progress",
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Record HTTP metrics for each request.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable[[Request], Awaitable[Response]]): The next handler in the middleware chain.

        Returns:
            Response: The HTTP response from the next handler.
        """
        request_info = get_request_info(request)
        in_progress_attrs = {
            "http.method": request_info.method,
            "http.path": request_info.route_path,
        }
        self._in_progress.add(1, attributes=in_progress_attrs)
        start_time = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            attrs: dict[str, str | int] = {
                "http.method": request_info.method,
                "http.path": request_info.route_path,
                "http.status_code": status_code,
            }
            self._in_progress.add(-1, attributes=in_progress_attrs)
            self._duration.record(duration_ms, attributes=attrs)
            self._counter.add(1, attributes=attrs)
