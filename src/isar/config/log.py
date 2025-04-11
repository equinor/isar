import logging
import logging.config
from importlib.resources import as_file, files

import yaml
from opencensus.ext.azure.log_exporter import AzureLogHandler
from uvicorn.logging import ColourizedFormatter

from isar.config.configuration_error import ConfigurationError
from isar.config.keyvault.keyvault_error import KeyvaultError
from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.settings import settings


def setup_loggers(keyvault: Keyvault) -> None:
    log_levels: dict = settings.LOG_LEVELS
    source = files("isar").joinpath("config").joinpath("logging.conf")
    with as_file(source) as f:
        log_config = yaml.safe_load(open(f))

    logging.config.dictConfig(log_config)

    handlers = []
    if settings.LOG_HANDLER_LOCAL_ENABLED:
        handlers.append(configure_console_handler(log_config=log_config))
    if settings.LOG_HANDLER_APPLICATION_INSIGHTS_ENABLED:
        handlers.append(
            configure_azure_handler(log_config=log_config, keyvault=keyvault)
        )

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


def configure_azure_handler(log_config: dict, keyvault: Keyvault) -> logging.Handler:
    connection_string: str
    try:
        connection_string = keyvault.get_secret(
            "application-insights-connection-string"
        ).value
    except KeyvaultError:
        message: str = (
            "CRITICAL ERROR: Missing connection string for"
            f" Application Insights in key vault '{keyvault.name}'."
        )
        print(f"\n{message} \n")
        raise ConfigurationError(message)

    handler = AzureLogHandler(connection_string=connection_string)
    handler.setLevel(log_config["root"]["level"])
    return handler
