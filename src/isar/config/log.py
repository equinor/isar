import importlib.resources as pkg_resources
import logging
import logging.config
import yaml
from uvicorn.logging import ColourizedFormatter
from opencensus.ext.azure.log_exporter import AzureLogHandler
from isar.config.settings import settings


def setup_loggers() -> None:
    log_levels: dict = settings.LOG_LEVELS
    with pkg_resources.path("isar.config", "logging.conf") as path:
        log_config = yaml.safe_load(open(path))

    logging.config.dictConfig(log_config)

    handlers = []
    if settings.LOG_HANDLER_LOCAL_ENABLED:
        handlers.append(configure_console_handler(log_config=log_config))
    if settings.LOG_HANDLER_APPLICATION_INSIGHTS_ENABLED:
        handlers.append(configure_azure_handler(log_config=log_config))

    for log_handler in handlers:
        for loggers in log_config["loggers"].keys():
            logging.getLogger(loggers).addHandler(log_handler)
            logging.getLogger(loggers).setLevel(log_levels[loggers])
        logging.getLogger().addHandler(log_handler)


def configure_console_handler(log_config: dict) -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setLevel(log_config["root"]["level"])
    handler.setFormatter(
        ColourizedFormatter(
            log_config["formatters"]["colourized"]["format"],
            style="{",
            use_colors=True,
        )
    )
    return handler


def configure_azure_handler(log_config: dict) -> logging.Handler:
    # Automatically gets connection string from env variable 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    handler = AzureLogHandler()
    handler.setLevel(log_config["root"]["level"])
    return handler
