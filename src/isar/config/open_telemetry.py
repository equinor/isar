import os
import logging
from fastapi import FastAPI

from opentelemetry import trace
from opentelemetry.sdk.resources import (
    Resource,
    SERVICE_NAME,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from azure.identity import DefaultAzureCredential


def setup_open_telemetry(app: FastAPI) -> None:
    # credential = DefaultAzureCredential()
    print("##############################################")
    print(os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"])
    service_name = os.getenv("OTEL_SERVICE_NAME", "my-fastapi-server")
    # ndpoint = "http://localhost:18889"  # Default endpoint for OTLP gRPC

    resource = Resource.create({SERVICE_NAME: service_name})

    tracer_provider = TracerProvider(resource=resource)
    # if endpoint:
    exporter = AzureMonitorTraceExporter(
        connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
    )
    # exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    log_provider = LoggerProvider(resource=resource)
    set_logger_provider(log_provider)

    log_exporter = AzureMonitorLogExporter(
        connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
        # credential=credential,
    )
    # if endpoint:
    #  log_exporter = OTLPLogExporter(endpoint=endpoint, insecure=True)
    log_provider.add_log_record_processor(
        BatchLogRecordProcessor(log_exporter, max_export_batch_size=1)
    )

    handler = LoggingHandler(logger_provider=log_provider)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.info
    root.info("OpenTelemetry logging initialized")

    api_logger = logging.getLogger("api")
    api_logger.addHandler(handler)

    api_logger.info("OpenTelemetry logging for API initialized")

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    log_provider.force_flush()
