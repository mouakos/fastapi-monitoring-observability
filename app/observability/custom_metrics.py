"""Custom metrics definitions for OpenTelemetry."""

import os

from opentelemetry import metrics

otel_service_name = os.getenv("OTEL_SERVICE_NAME", "fastapi-app")

meter = metrics.get_meter(f"{otel_service_name}.metrics")

HTTP_REQUEST_COUNTER = meter.create_counter(
    name="http_request_count",
    description="Count of HTTP requests received",
)

HTTP_REQUEST_DURATION_MS = meter.create_histogram(
    name="http_request_duration_ms",
    description="Duration of HTTP requests in milliseconds",
)

HTTP_REQUEST_IN_PROGRESS = meter.create_up_down_counter(
    name="http_request_in_progress",
    description="Number of HTTP requests currently in progress",
)
