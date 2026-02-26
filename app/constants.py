"""Constants for the FastAPI application."""

# Paths to exclude from logging and tracing to reduce noise in logs and traces
EXCLUDED_PATHS = {
    "/openapi.json",
    "/docs",
    "/redoc",
    "/health",
    "/metrics",
    "/favicon.ico",
}
