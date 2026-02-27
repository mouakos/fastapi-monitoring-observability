"""This is the main entry point for the FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from loguru import logger

from app.exceptions import register_exception_handlers
from app.logging import setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.otel import setup_otlp
from app.routes import router
from app.settings import config

load_dotenv()

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Lifespan function to perform startup and shutdown tasks."""
    logger.info("Application is starting up...")
    # Perform any startup tasks here (e.g., connect to database, initialize resources)
    logger.info("Application startup completed.")
    yield
    logger.info("Application is shutting down...")
    # Perform any shutdown tasks here (e.g., close database connections, clean up resources)
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
# Set up OpenTelemetry tracing and metrics
setup_otlp(app)

# Add custom request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add custom metrics middleware to track request metrics
app.add_middleware(MetricsMiddleware)

# Register exception handlers
register_exception_handlers(app)

# Add API routes
app.include_router(router)
