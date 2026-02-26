"""This module contains the global exception handlers for the FastAPI application."""

import http

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance to register the exception handlers with.
    """

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, _: Exception) -> JSONResponse:
        """Handle unhandled exceptions globally, log the error, and return a standardized JSON response.

        Args:
            request (Request): The incoming HTTP request that caused the exception.
            _: The unhandled exception that was raised during request processing.

        Returns:
            JSONResponse: A standardized JSON response with status code 500 and error details.
        """
        route = request.scope.get("route")
        http_path = route.path if route else request.url.path
        logger.bind(
            http_method=request.method,
            http_path=http_path,
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            http_status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
        ).exception("unhandled_exception")

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )
