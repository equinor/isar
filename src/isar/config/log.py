import importlib.resources as pkg_resources
import logging
import logging.config

import yaml
from uvicorn.logging import ColourizedFormatter

from isar.config.settings import settings


def setup_logger():
    log_levels: dict = settings.LOG_LEVELS
    with pkg_resources.path("isar.config", "logging.conf") as path:
        log_config = yaml.safe_load(open(path))

    log_handler = logging.StreamHandler()

    log_handler.setLevel(log_config["root"]["level"])
    log_handler.setFormatter(
        ColourizedFormatter(
            log_config["formatters"]["colourized"]["format"],
            style="{",
            use_colors=True,
        )
    )

    logging.config.dictConfig(log_config)

    for loggers in log_config["loggers"].keys():
        logging.getLogger(loggers).addHandler(log_handler)
        logging.getLogger(loggers).setLevel(log_levels[loggers])
    logging.getLogger().addHandler(log_handler)
