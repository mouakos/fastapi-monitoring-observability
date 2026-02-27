"""This module contains the global exception handlers for the FastAPI application."""

import http

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.utils import get_request_info


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
        request_info = get_request_info(request)
        logger.bind(
            http_method=request_info.method,
            http_path=request_info.route_path,
            client_ip=request_info.client_ip,
            user_agent=request_info.user_agent,
            http_status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
        ).exception("unhandled_exception")

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )
