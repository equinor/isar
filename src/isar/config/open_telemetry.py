import logging

from azure.monitor.opentelemetry.exporter import (
    AzureMonitorLogExporter,
    AzureMonitorTraceExporter,
)
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from isar.config.log import load_log_config
from isar.config.settings import settings


def setup_open_telemetry(app: FastAPI) -> None:
    if not settings.LOG_HANDLER_APPLICATION_INSIGHTS_ENABLED:
        return
    trace_exporter, log_exporter = get_azure_monitor_exporters()

    service_name = settings.OPEN_TELEMETRY_SERVICE_NAME
    resource = Resource.create({SERVICE_NAME: service_name})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    log_provider = LoggerProvider(resource=resource)
    set_logger_provider(log_provider)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    handler = LoggingHandler(logger_provider=log_provider)
    attach_loggers_for_open_telemetry(handler)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)


def attach_loggers_for_open_telemetry(handler: LoggingHandler):
    log_config = load_log_config()

    for logger_name in log_config["loggers"].keys():
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)


def get_azure_monitor_exporters() -> (
    tuple[AzureMonitorTraceExporter, AzureMonitorLogExporter]
):
    """
    If connection string is defined in environment variables, then use it to create Azure Monitor Exporters.
    Else use Azure Managed Identity to create Azure Monitor Exporters.
    """
    connection_string = settings.APPLICATIONINSIGHTS_CONNECTION_STRING
    trace_exporter = AzureMonitorTraceExporter(connection_string=connection_string)
    log_exporter = AzureMonitorLogExporter(connection_string=connection_string)

    return trace_exporter, log_exporter
