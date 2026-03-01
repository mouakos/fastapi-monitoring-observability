"""This is the main entry point for the FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.correlation_id import setup_correlation_id
from app.exceptions import register_exception_handlers
from app.logging import setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.otel import setup_otlp
from app.routes import router
from app.settings import config

# ---------------------------------------------------------------------------
# Logging — must be initialized before anything else
# ---------------------------------------------------------------------------

setup_logging()

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Lifespan function to perform startup and shutdown tasks."""
    logger.info("Application is starting up...")
    logger.info("Application startup completed.")
    yield
    logger.info("Application is shutting down...")
    logger.info("Application shutting down completed.")


app = FastAPI(
    lifespan=lifespan,
    title="FastAPI Monitoring and Observability",
    version=config.api_version,
    servers=[],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/mit/",
    },
    contact={
        "name": "Stephane Mouako",
        "url": "https://github.com/mouakos",
    },
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "layout": "BaseLayout",
        "filter": True,
        "tryItOutEnabled": True,
        "onComplete": "Ok",
    },
)

# ---------------------------------------------------------------------------
# Observability — OpenTelemetry tracing, metrics, and logs
# ---------------------------------------------------------------------------

setup_otlp(app)

# ---------------------------------------------------------------------------
# Middleware — registered in LIFO order, so last added runs first
#   execution order: CorrelationId → RequestLogging → Metrics → app
# ---------------------------------------------------------------------------

app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)
setup_correlation_id(app)  # adds CorrelationIdMiddleware (outermost)

# ---------------------------------------------------------------------------
# Exception handlers & routes
# ---------------------------------------------------------------------------

register_exception_handlers(app)
app.include_router(router)
