"""Monitoring and observability endpoints."""

import random
from asyncio import sleep

from fastapi import APIRouter, HTTPException
from loguru import logger

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
        "log_format": "json" if config.log_serialized else "text",
        "otel_enabled": str(config.otel_enabled),
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
