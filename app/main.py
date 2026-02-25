"""This is the main entry point for the FastAPI application."""

from fastapi import FastAPI

from app.middleware import RequestLoggingMiddleware
from app.observability.logging import setup_logging

setup_logging()

app = FastAPI(
    title="FastAPI Monitoring and Observability",
    version="1.0.0",
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
    openapi_tags=[
        {
            "name": "Root",
            "description": "API root endpoint with welcome message.",
        },
    ],
)
app.add_middleware(RequestLoggingMiddleware)


@app.get(
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
