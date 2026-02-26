"""Middleware for the FastAPI application."""

import time
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)

            # Update status_code binding with actual response status
            log = log.bind(http_status_code=response.status_code, duration_ms=duration_ms)

            # Log at different levels based on status code
            if response.status_code >= 500:
                log.error("http_request")
            elif response.status_code >= 400:
                log.warning("http_request")
            else:
                log.info("http_request")

            return response
        except Exception:
            # In case of unhandled exceptions, log the error with status code 500
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            log.bind(http_status_code=500, duration_ms=duration_ms).exception("unhandled_exception")
            return JSONResponse(content={"detail": "Internal Server Error"}, status_code=500)

    def _get_path_template(self, request: Request) -> str:
        """Get the route path template for the incoming HTTP request.

        Args:
            request (Request): The incoming HTTP request object.

        Returns:
            str: The route path template for the incoming HTTP request.
        """
        route = request.scope.get("route")
        return route.path if route else request.url.path
