"""OTLP setup for FastAPI application."""

from typing import Any

from fastapi import FastAPI
from loguru import logger
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.logging import LOG_FORMAT
from app.settings import EXCLUDED_PATHS, config


def inject_trace_context_to_logger(record: dict[str, Any]) -> None:
    """Inject trace_id and span_id into Loguru logger context.

    This function is used as a Loguru logger patcher to include OpenTelemetry trace context in all log records.
    It retrieves the current span and, if it is recording, adds the trace_id and span_id to the log record's extra fields.

    Args:
        record: The log record to modify.
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()

    if span_context and span_context.is_valid:
        span_context = span.get_span_context()
        record["extra"]["trace_id"] = trace.format_trace_id(span_context.trace_id)
        record["extra"]["span_id"] = trace.format_span_id(span_context.span_id)


def setup_otlp_logs(resource: Resource) -> None:
    """Set up OpenTelemetry logging for the FastAPI application.

    Args:
        resource: The OpenTelemetry resource to associate with log records.
    """
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    exporter = OTLPLogExporter(
        endpoint=config.otel_exporter_otlp_endpoint,
        insecure=config.otel_exporter_otlp_insecure,
    )

    # Add batch processor for efficient log handling
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    # Forward Loguru records to the OTLP pipeline.
    # The SDK automatically attaches trace_id/span_id to each OTLP record when an active span exists.
    handler = LoggingHandler(logger_provider=logger_provider)
    logger.add(
        handler,
        level=config.log_level,
        format=LOG_FORMAT,
        enqueue=False,  # Do not use Loguru's queue since OTLP exporter handles batching
        serialize=config.log_serialized,
    )


def setup_otlp_metrics(resource: Resource) -> MeterProvider:
    """Set up OpenTelemetry metrics for the FastAPI application.

    Args:
        resource: The OpenTelemetry resource to associate with metrics.

    Returns:
        MeterProvider: The configured OpenTelemetry MeterProvider instance.
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


def setup_otlp_traces(resource: Resource) -> TracerProvider:
    """Set up OpenTelemetry tracing for the FastAPI application.

    Args:
        resource: The OpenTelemetry resource to associate with traces.

    Returns:
        TracerProvider: The configured OpenTelemetry TracerProvider instance.
    """
    trace_provider = TracerProvider(resource=resource)
    otlp_span_exporter = OTLPSpanExporter(
        insecure=config.otel_exporter_otlp_insecure,
        endpoint=config.otel_exporter_otlp_endpoint,
    )
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
    trace.set_tracer_provider(trace_provider)

    return trace_provider


def setup_otlp(app: FastAPI) -> None:
    """Set up OpenTelemetry tracing, metrics and logging for the FastAPI application.

    Args:
        app: The FastAPI application instance to instrument with OpenTelemetry.
    """
    if not config.otel_enabled:
        logger.info("opentelemetry_disabled")
        return

    resource = Resource.create(
        {
            "deployment.environment": config.environment,
            "service.version": config.api_version,
            "service.name": config.otel_service_name,
        }
    )
    trace_provider = setup_otlp_traces(resource)
    meter_provider = setup_otlp_metrics(resource)
    setup_otlp_logs(resource)

    # Patch Loguru records with trace_id/span_id for stdout/file sinks
    logger.configure(patcher=inject_trace_context_to_logger)  # type: ignore [arg-type]

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace_provider,
        meter_provider=meter_provider,
        excluded_urls=",".join(EXCLUDED_PATHS),
    )
