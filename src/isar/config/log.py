import logging
import logging.config
from importlib.resources import as_file, files

import yaml
from uvicorn.logging import ColourizedFormatter

from isar.config.settings import settings


def setup_loggers() -> None:
    log_levels: dict = settings.LOG_LEVELS
    log_config = load_log_config()

    logging.config.dictConfig(log_config)

    handlers = []
    if settings.LOG_HANDLER_LOCAL_ENABLED:
        handlers.append(configure_console_handler(log_config=log_config))

    for log_handler in handlers:
        for loggers in log_config["loggers"].keys():
            logging.getLogger(loggers).addHandler(log_handler)
            logging.getLogger(loggers).setLevel(log_levels[loggers])
        logging.getLogger().addHandler(log_handler)


def load_log_config():
    source = files("isar").joinpath("config").joinpath("logging.conf")
    with as_file(source) as f:
        log_config = yaml.safe_load(open(f))
    return log_config


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
