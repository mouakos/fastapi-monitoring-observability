"""Tracing setup for the FastAPI application."""

from typing import Any

from fastapi import FastAPI
from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.constants import EXCLUDED_PATHS
from app.observability.otel_resource import build_resource


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


def setup_otlp_tracing(app: FastAPI) -> None:
    """Set up OpenTelemetry tracing for the FastAPI application using gRPC OTLP exporter.

    Args:
        app: The FastAPI application instance to instrument with OpenTelemetry tracing.
    """
    provider = TracerProvider(resource=build_resource())
    exporter = OTLPSpanExporter(insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # This adds trace_id and span_id to all log records if there is an active span
    logger.configure(patcher=inject_trace_context_to_logger)  # type: ignore [arg-type]

    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=provider, excluded_urls=",".join(EXCLUDED_PATHS)
    )
