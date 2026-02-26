"""This module defines the OpenTelemetry Resource for the application."""

from opentelemetry.sdk.resources import Resource

from app.settings import config


def build_resource() -> Resource:
    """Build an OpenTelemetry Resource with service metadata from configuration."""
    return Resource.create(
        {
            "deployment.environment": config.environment,
            "service.version": config.api_version,
        }
    )
