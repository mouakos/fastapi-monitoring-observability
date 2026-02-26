"""This is the main entry point for the FastAPI application."""

from dotenv import load_dotenv
from fastapi import FastAPI

from app.api import router
from app.middleware import RequestLoggingMiddleware
from app.observability.logging import setup_logging
from app.observability.tracing import setup_otlp_tracing
from app.settings import config

load_dotenv()

setup_logging()

app = FastAPI(
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
# Add custom request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Set up OpenTelemetry tracing
setup_otlp_tracing(app)

# Add API routes
app.include_router(router)
