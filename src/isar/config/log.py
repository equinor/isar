import logging
import logging.config
import os
from importlib.resources import as_file, files

import yaml
from uvicorn.logging import ColourizedFormatter

from isar.config.settings import settings

from .settings import Settings


def setup_loggers() -> None:
    log_config = load_log_config()

    logging.config.dictConfig(log_config)

    env_log_levels = {}
    for env_var, value in os.environ.items():
        if env_var.endswith("_LOG_LEVEL"):
            log_name = env_var.split("_LOG_LEVEL")[0].lower()
            env_log_levels[log_name] = value.upper()

    handlers = []
    if settings.LOG_HANDLER_LOCAL_ENABLED:
        handlers.append(
            configure_console_handler(log_config=log_config, settings=settings)
        )

    for log_handler in handlers:
        for logger_name, logger_config in log_config["loggers"].items():
            logger = logging.getLogger(logger_name)
            logger.addHandler(log_handler)
            if "level" in logger_config:
                logger.setLevel(logger_config["level"])
            if logger_name in env_log_levels:
                logger.setLevel(env_log_levels[logger_name])
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        if "level" in log_config.get("root", {}):
            root_logger.setLevel(log_config["root"]["level"])


def load_log_config():
    source = files("isar").joinpath("config").joinpath("logging.conf")
    with as_file(source) as f:
        log_config = yaml.safe_load(open(f))
    return log_config


def configure_console_handler(log_config: dict, settings: Settings) -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setLevel(log_config["root"]["level"])
    if settings.DEBUG_LOG_FORMATTER:
        handler.setFormatter(
            ColourizedFormatter(
                log_config["formatters"]["debug-formatter"]["format"],
                style="{",
                use_colors=True,
            )
        )
    else:
        handler.setFormatter(
            ColourizedFormatter(
                log_config["formatters"]["colourized"]["format"],
                style="{",
                use_colors=True,
            )
        )
    return handler
