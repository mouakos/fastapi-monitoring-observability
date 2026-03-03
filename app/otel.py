"""OpenTelemetry (OTLP) setup for the FastAPI application.

Configures the three pillars of observability over gRPC OTLP exporters:
- Traces  : BatchSpanProcessor → OTLPSpanExporter → collector
- Metrics : PeriodicExportingMetricReader → OTLPMetricExporter → collector
- Logs    : Loguru → LoggingHandler → BatchLogRecordProcessor → OTLPLogExporter → collector

All signals share a common Resource that identifies the service. FastAPI HTTP
spans are captured via FastAPIInstrumentor; outbound HTTPX calls are captured
via HTTPXClientInstrumentor (injects traceparent into outgoing request headers).
"""

from typing import Any

from fastapi import FastAPI
from loguru import logger
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.logging import LOG_FORMAT, register_log_patcher
from app.settings import config

# ---------------------------------------------------------------------------
# Log patcher — injects trace context into every Loguru record
# ---------------------------------------------------------------------------


def _inject_trace_context_to_logger(record: dict[str, Any]) -> None:
    """Stamp the active OpenTelemetry trace_id and span_id onto a Loguru log record.

    Registered as a Loguru patcher so every log record emitted inside an active
    span carries the trace and span IDs. This allows log entries to be correlated
    with traces in the observability backend (e.g. Grafana Tempo).

    Does nothing when there is no active or valid span (e.g. startup logs).

    Args:
        record: The Loguru log record to modify.
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()

    if span_context and span_context.is_valid:
        record["extra"]["trace_id"] = trace.format_trace_id(span_context.trace_id)
        record["extra"]["span_id"] = trace.format_span_id(span_context.span_id)


# ---------------------------------------------------------------------------
# Private setup helpers
# ---------------------------------------------------------------------------


def _setup_traces(resource: Resource) -> TracerProvider:
    """Create a TracerProvider with a gRPC OTLP span exporter.

    Spans are exported asynchronously via BatchSpanProcessor. The provider is
    registered globally so opentelemetry.trace.get_tracer() picks it up.

    Args:
        resource: Service metadata attached to every exported span.

    Returns:
        The configured TracerProvider.
    """
    trace_provider = TracerProvider(resource=resource)
    otlp_span_exporter = OTLPSpanExporter(
        insecure=config.otel_exporter_otlp_insecure,
        endpoint=config.otel_exporter_otlp_endpoint,
    )
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
    trace.set_tracer_provider(trace_provider)
    return trace_provider


def _setup_metrics(resource: Resource) -> MeterProvider:
    """Create a MeterProvider with a gRPC OTLP metric exporter.

    Metrics are scraped at the interval defined by config.otel_metric_export_interval
    and pushed via PeriodicExportingMetricReader. The provider is registered globally
    so opentelemetry.metrics.get_meter() picks it up.

    Args:
        resource: Service metadata attached to every exported metric.

    Returns:
        The configured MeterProvider.
    """
    otlp_metric_exporter = OTLPMetricExporter(
        insecure=config.otel_exporter_otlp_insecure,
        endpoint=config.otel_exporter_otlp_endpoint,
    )
    reader = PeriodicExportingMetricReader(
        otlp_metric_exporter, export_interval_millis=config.otel_metric_export_interval
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)
    return meter_provider


def _setup_logs(resource: Resource) -> None:
    """Bridge Loguru into the OTLP log pipeline.

    Creates a LoggerProvider with a gRPC OTLP exporter, then attaches an
    OpenTelemetry LoggingHandler as a Loguru sink. Every record emitted by
    Loguru is forwarded to the collector via BatchLogRecordProcessor.

    Args:
        resource: Service metadata attached to every exported log record.
    """
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    exporter = OTLPLogExporter(
        endpoint=config.otel_exporter_otlp_endpoint,
        insecure=config.otel_exporter_otlp_insecure,
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    # Forward Loguru records to the OTLP pipeline.
    # The SDK automatically attaches trace_id/span_id to each OTLP record when an active span exists.
    handler = LoggingHandler(logger_provider=logger_provider)
    logger.add(
        handler,
        level=config.log_level,
        format=LOG_FORMAT,
        enqueue=False,  # OTLP exporter handles batching; no need for Loguru's queue
        serialize=config.log_serialized,
    )


def _build_resource() -> Resource:
    """Build the OpenTelemetry Resource that identifies this service.

    The resource attributes are attached to every span, metric, and log record
    exported to the collector, enabling filtering and grouping in the backend.

    Returns:
        A Resource populated with service name and deployment environment.
    """
    return Resource.create(
        {
            "service.name": config.otel_service_name,
            "deployment.environment": config.environment,
        }
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def setup_otlp(app: FastAPI) -> None:
    """Initialise OpenTelemetry tracing, metrics, and logging for the FastAPI application.

    Skips setup entirely when config.otel_enabled is False (e.g. local dev).

    Steps performed when enabled:
    1. Build a shared Resource with service metadata.
    2. Configure OTLP exporters for traces, metrics, and logs.
    3. Instrument FastAPI to capture incoming HTTP spans and metrics.
    4. Instrument HTTPX to capture outbound HTTP spans and inject traceparent headers.
    5. Register a Loguru patcher to stamp trace_id/span_id on every log record.

    Args:
        app: The FastAPI application instance to instrument.
    """
    if not config.otel_enabled:
        logger.info("opentelemetry_disabled")
        return

    resource = _build_resource()
    trace_provider = _setup_traces(resource)
    meter_provider = _setup_metrics(resource)
    _setup_logs(resource)

    # Incoming HTTP requests
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace_provider,
        meter_provider=meter_provider,
    )
    # Outbound HTTP calls — injects traceparent into request headers
    HTTPXClientInstrumentor().instrument()

    # Register the trace context patcher once at startup
    register_log_patcher(_inject_trace_context_to_logger)
