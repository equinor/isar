import logging
from urllib.parse import urljoin

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as OTLPHttpLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as OTLPHttpMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHttpSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from isar.config.log import load_log_config
from isar.config.settings import settings

logging.getLogger("opentelemetry.sdk").setLevel(logging.CRITICAL)


def setup_open_telemetry(app: FastAPI) -> None:

    resource = Resource.create(
        {
            SERVICE_NAME: settings.ROBOT_NAME,
            "isar.id": settings.ISAR_ID,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    log_provider = LoggerProvider(resource=resource)
    metric_readers: list[PeriodicExportingMetricReader] = []

    otlp_exporter_endpoint = settings.OPEN_TELEMETRY_OTLP_EXPORTER_ENDPOINT
    if otlp_exporter_endpoint:
        print(f"[OTEL] OTLP exporters enabled, endpoint={otlp_exporter_endpoint}")
        otlp_trace_exporter, otlp_log_exporter, otlp_metric_exporter = (
            get_otlp_exporters(otlp_exporter_endpoint)
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))

        log_provider.add_log_record_processor(
            BatchLogRecordProcessor(otlp_log_exporter)
        )

        metric_readers.append(PeriodicExportingMetricReader(otlp_metric_exporter))

    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)

    set_logger_provider(log_provider)
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)

    handler = LoggingHandler(logger_provider=log_provider)
    attach_loggers_for_open_telemetry(handler)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)


def attach_loggers_for_open_telemetry(handler: LoggingHandler) -> None:
    log_config = load_log_config()

    for logger_name in log_config["loggers"].keys():
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)


def get_otlp_exporters(
    endpoint: str,
) -> tuple[OTLPHttpSpanExporter, OTLPHttpLogExporter, OTLPHttpMetricExporter]:
    base = endpoint.rstrip("/") + "/"
    trace_ep = urljoin(base, "v1/traces")
    log_ep = urljoin(base, "v1/logs")
    metric_ep = urljoin(base, "v1/metrics")

    print("[OTEL] Using HTTP/Protobuf protocol for OpenTelemetry export")
    print(f"[OTEL]  traces → {trace_ep}")
    print(f"[OTEL]  logs   → {log_ep}")
    print(f"[OTEL]  metrics→ {metric_ep}")

    return (
        OTLPHttpSpanExporter(endpoint=trace_ep),
        OTLPHttpLogExporter(endpoint=log_ep),
        OTLPHttpMetricExporter(endpoint=metric_ep),
    )
