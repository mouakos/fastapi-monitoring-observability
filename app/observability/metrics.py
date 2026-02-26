"""Metrics setup for the FastAPI application."""

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from app.observability.otel_resource import build_resource


def setup_otlp_metrics() -> None:
    """Set up OpenTelemetry metrics for the FastAPI application using gRPC OTLP exporter."""
    exporter = OTLPMetricExporter(insecure=True)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)

    provider = MeterProvider(resource=build_resource(), metric_readers=[reader])
    metrics.set_meter_provider(provider)
