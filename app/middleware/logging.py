"""Middleware for logging HTTP requests."""

import time
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils import get_request_info


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming HTTP requests."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Middleware to log incoming HTTP requests.

        Args:
            request(Request): The incoming HTTP request.
            call_next(Callable[[Request], Awaitable[Response]]): The next handler in the middleware chain.

        Returns:
            Response: The HTTP response from the next handler.
        """
        request_info = get_request_info(request)

        # Bind relevant information to the logger for structured logging
        log = logger.bind(
            http_method=request_info.method,
            http_path=request_info.route_path,
            client_ip=request_info.client_ip,
            user_agent=request_info.user_agent,
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)

        # Log the request with the response status code and duration
        log.bind(http_status_code=response.status_code, duration_ms=duration_ms).info(
            "http_request"
        )

        return response
