"""Middleware for the FastAPI application."""

import time
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.constants import EXCLUDED_PATHS


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
        # Skip logging for excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Use Loguru's contextualize to add request_id to the logger context for this request

        client_host = request.client.host if request.client else "unknown"
        route_path = self._get_path_template(request)
        user_agent = request.headers.get("user-agent")

        # Bind relevant information to the logger for structured logging
        log = logger.bind(
            http_method=request.method,
            http_path=route_path,
            client_ip=client_host,
            user_agent=user_agent,
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)

        # Log the request with the response status code and duration
        log.bind(http_status_code=response.status_code, duration_ms=duration_ms).info(
            "http_request"
        )

        return response

    def _get_path_template(self, request: Request) -> str:
        """Get the route path template for the incoming HTTP request.

        Args:
            request (Request): The incoming HTTP request object.

        Returns:
            str: The route path template for the incoming HTTP request.
        """
        route = request.scope.get("route")
        return route.path if route else request.url.path
