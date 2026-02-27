"""Configuration settings for the FastAPI application."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Configuration settings for the FastAPI application."""

    # Logging settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["text", "json"] = "text"
    log_to_file: bool = False

    # Application settings
    api_version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    environment: Literal["development", "staging", "production"] = "development"

    # OTLP settings
    otel_service_name: str = "fastapi-app"
    otel_exporter_otlp_traces_endpoint: str = "localhost:4317"
    otel_exporter_otlp_metrics_endpoint: str = "localhost:4317"
    otel_exporter_otlp_traces_insecure: bool = True
    otel_exporter_otlp_metrics_insecure: bool = True
    otel_metric_export_interval: int = 5000
    otel_sdk_disabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="forbid"
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
