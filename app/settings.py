"""Configuration settings for the FastAPI application."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Configuration settings for the FastAPI application."""

    # Logging settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_serialized: bool = False
    log_to_file: bool = False

    # Application settings
    api_version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    environment: Literal["development", "staging", "production"] = "development"

    # OTLP settings
    otel_service_name: str = "fastapi-app"
    otel_exporter_otlp_endpoint: str = "localhost:4317"
    otel_exporter_otlp_insecure: bool = True
    otel_enabled: bool = False
    otel_metric_export_interval: int = 5000  # in milliseconds

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


config = AppConfig()

# Paths to exclude from logging and tracing to reduce noise in logs and traces
EXCLUDED_PATHS: frozenset[str] = frozenset(
    {
        "/openapi.json",
        "/docs",
        "/redoc",
        "/health",
        "/metrics",
        "/favicon.ico",
    }
)
