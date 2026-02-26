"""Tracing and metrics setup for the FastAPI application."""

from typing import Any

from fastapi import FastAPI
from loguru import logger
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.constants import EXCLUDED_PATHS
from app.settings import config


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


def setup_otlp(app: FastAPI) -> None:
    """Set up OpenTelemetry tracing for the FastAPI application using gRPC OTLP exporter.

    Args:
        app: The FastAPI application instance to instrument with OpenTelemetry tracing.
    """
    resource = Resource.create(
        {"deployment.environment": config.environment, "service.version": config.api_version}
    )
    trace_provider = TracerProvider(resource=resource)
    otlp_span_exporter = OTLPSpanExporter(insecure=True)
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
    trace.set_tracer_provider(trace_provider)

    otlp_metric_exporter = OTLPMetricExporter(insecure=True)
    reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=5000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # This adds trace_id and span_id to all log records if there is an active span
    logger.configure(patcher=inject_trace_context_to_logger)  # type: ignore [arg-type]

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace_provider,
        meter_provider=meter_provider,
        excluded_urls=",".join(EXCLUDED_PATHS),
    )
