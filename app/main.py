"""This is the main entry point for the FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api import router
from app.exceptions import register_exception_handlers
from app.logging import setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.otel import setup_otlp
from app.settings import config

# ---------------------------------------------------------------------------
# Logging — must be initialized before anything else
# ---------------------------------------------------------------------------

# Silencing uvicorn.access logs since they are already captured by the RequestLoggingMiddleware
# and would otherwise be duplicated in the logs.
_SILENCED_LOGGERS = ["uvicorn.access", "httpx", "httpcore"]

setup_logging(silenced_loggers=_SILENCED_LOGGERS)

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Lifespan function to perform startup and shutdown tasks."""
    # Perform any additional startup tasks here (e.g. warmup, preloading) if needed
    yield
    await logger.complete()  # flush enqueued log records before process exits


app = FastAPI(
    lifespan=lifespan,
    title="FastAPI Monitoring and Observability",
    version=config.api_version,
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/mit/",
    },
    contact={
        "name": "Stephane Mouako",
        "url": "https://github.com/mouakos",
    },
)

# ---------------------------------------------------------------------------
# Observability — OpenTelemetry tracing, metrics, and logs
# ---------------------------------------------------------------------------

setup_otlp(app)

# ---------------------------------------------------------------------------
# Middleware — registered in LIFO order, so last added runs first
#   execution order: RequestLogging → Metrics → app
# ---------------------------------------------------------------------------

app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# ---------------------------------------------------------------------------
# Exception handlers & routes
# ---------------------------------------------------------------------------

register_exception_handlers(app)
app.include_router(router)
