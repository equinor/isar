import json
import logging
from dataclasses import is_dataclass
from logging import Logger
from pathlib import Path
from typing import Any, Optional

from dacite import Config, from_dict

logger: Logger = logging.getLogger("api")


class BaseReader:
    @staticmethod
    def read_json(location: Path) -> dict:
        with open(location) as json_file:
            return json.load(json_file)

    @staticmethod
    def dict_to_dataclass(
        dataclass_dict: dict,
        target_dataclass: Any,
        cast_config: list = [],
        strict_config: bool = False,
    ) -> Optional[Any]:
        if not is_dataclass(target_dataclass):
            raise BaseReaderError("{target_dataclass} is not a dataclass")
        generated_dataclass = from_dict(
            data_class=target_dataclass,
            data=dataclass_dict,
            config=Config(cast=cast_config, strict=strict_config),
        )
        return generated_dataclass


class BaseReaderError(Exception):
    pass
