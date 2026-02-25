"""Middleware for the FastAPI application."""

import time
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming HTTP requests with method, path, status code, and duration."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware to log incoming HTTP requests with method, path, status code, and duration.

        Args:
            request(Request): The incoming HTTP request.
            call_next(Callable[[Request], Awaitable[Response]]): The next handler in the middleware chain.

        Returns:
            Response: The HTTP response from the next handler.
        """
        start = time.perf_counter()
        status_code = 500  # Default to 500 in case of unhandled exceptions
        client_host = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0

            # Use route path for logging to avoid logging query parameters
            route = request.scope.get("route")
            route_path = route.path if route else request.url.path
            log_message = "http_request"
            log = logger.bind(
                method=request.method,
                path=route_path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                client_host=client_host,
            )
            if status_code >= 500:
                log.error(log_message)
            else:
                log.info(log_message)
