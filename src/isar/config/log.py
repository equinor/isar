import logging
import logging.config

import yaml
from uvicorn.logging import ColourizedFormatter


def setup_logger():
    log_config = yaml.safe_load(open(f"./src/isar/config/logging.conf"))
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
    logging.getLogger().addHandler(log_handler)
