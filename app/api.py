"""This module contains the API routes for the FastAPI application."""

import random
from asyncio import sleep

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from app.settings import config

router = APIRouter()


@router.get(
    "/",
    response_model=dict[str, str],
    summary="Root Endpoint",
    description="Returns a welcome message.",
    tags=["Root"],
)
def read_root() -> dict[str, str]:
    """Root endpoint that returns a simple JSON response."""
    return {
        "message": "Welcome to the FastAPI application! Please visit /docs for API documentation."
    }


# ======================
# Monitoring & Observability Endpoints
# ======================


@router.get(
    "/health",
    response_model=dict[str, str],
    summary="Health Check",
    description="Basic health check endpoint. Returns healthy if the service is running.",
    tags=["Monitoring"],
)
def health_check() -> dict[str, str]:
    """Health check endpoint for basic liveness probe."""
    return {"status": "healthy"}


@router.get(
    "/info",
    response_model=dict[str, str],
    summary="Application Info",
    description="Returns application version, environment, and configuration details.",
    tags=["Monitoring"],
)
def app_info() -> dict[str, str]:
    """Application info endpoint showing version and environment."""
    return {
        "version": config.api_version,
        "environment": config.environment,
        "log_level": config.log_level,
        "log_format": config.log_format,
    }


@router.get(
    "/slow",
    summary="Slow Endpoint",
    description="Endpoint with configurable delay to test timeout and performance monitoring.",
    tags=["Monitoring"],
)
async def slow_endpoint(delay: float = 2.0) -> dict[str, str]:
    """Slow endpoint to test latency monitoring and timeouts."""
    logger.warning(f"Slow endpoint called with delay of {delay} seconds")
    await sleep(delay)
    logger.info(f"Slow endpoint completed after {delay} seconds")
    return {"message": f"Response after delay of {delay} seconds"}


@router.get(
    "/random-status",
    summary="Random Status Code",
    description="Returns random HTTP status codes for testing error rate monitoring.",
    tags=["Monitoring"],
)
def random_status() -> dict[str, str]:
    """Randomly return different status codes for testing error rate monitoring."""
    status_codes = [200, 200, 200, 201, 400, 404, 500]
    status = random.choice(status_codes)

    logger.info(f"Random status generated: {status}")

    if status >= 400:
        logger.warning(f"Triggering random error: {status}")
        raise HTTPException(status_code=status, detail=f"Random error with status {status}")

    return {"status": str(status), "message": "Success"}


@router.get(
    "/load-test",
    summary="Load Test Endpoint",
    description="Simple endpoint for load testing with minimal processing.",
    tags=["Monitoring"],
)
def load_test_endpoint(count: int = 1) -> dict[str, int]:
    """Simple endpoint for load testing."""
    result = sum(range(count))
    return {"count": count, "result": result}


# ======================
# Error Simulation Endpoints
# ======================


@router.get(
    "/error/400",
    summary="Bad Request Error",
    description="Triggers a 400 Bad Request error for testing error handling.",
    tags=["Errors"],
)
def bad_request() -> None:
    """Simulates a bad request error."""
    raise HTTPException(status_code=400, detail="Bad request example")


@router.get(
    "/error/401",
    summary="Unauthorized Error",
    description="Triggers a 401 Unauthorized error for testing authentication failures.",
    tags=["Errors"],
)
def unauthorized() -> None:
    """Simulates an unauthorized access error."""
    raise HTTPException(status_code=401, detail="Unauthorized example")


@router.get(
    "/error/404",
    summary="Not Found Error",
    description="Triggers a 404 Not Found error for testing missing resource handling.",
    tags=["Errors"],
)
def not_found() -> None:
    """Simulates a resource not found error."""
    raise HTTPException(status_code=404, detail="Resource not found")


class Item(BaseModel):
    """Model for item validation testing."""

    name: str
    price: float


@router.post(
    "/error/validation",
    summary="Validation Error",
    description="Triggers a 422 Unprocessable Entity error by sending invalid data.",
    tags=["Errors"],
)
def validation_error(item: Item) -> Item:
    """Endpoint to test request validation errors."""
    return item


@router.get(
    "/error/500-controlled",
    summary="Controlled Server Error",
    description="Triggers a controlled 500 Internal Server Error for testing error responses.",
    tags=["Errors"],
)
def controlled_500() -> None:
    """Simulates a controlled server error."""
    raise HTTPException(status_code=500, detail="Controlled server error")


@router.get(
    "/error/500-crash",
    summary="Unhandled Exception",
    description="Triggers an unhandled division by zero error to simulate application crashes.",
    tags=["Errors"],
)
def crash() -> float:
    """Simulates an unhandled exception causing a crash."""
    return 1 / 0


@router.get(
    "/error/timeout",
    summary="Timeout Simulation",
    description="Simulates a slow endpoint that takes 10 seconds to respond.",
    tags=["Errors"],
)
async def timeout() -> dict[str, str]:
    """Simulates a slow request that might timeout."""
    await sleep(10)
    return {"message": "Finished after delay"}


@router.get(
    "/error/external",
    summary="External Service Failure",
    description="Simulates an external service failure with a RuntimeError.",
    tags=["Errors"],
)
def external_failure() -> None:
    """Simulates an external service dependency failure."""
    raise RuntimeError("External service failed")
