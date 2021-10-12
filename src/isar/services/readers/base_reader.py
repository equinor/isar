import json
import logging
from dataclasses import is_dataclass
from json import JSONDecodeError
from logging import Logger
from pathlib import Path
from typing import Any, Optional

from dacite import Config, MissingValueError, WrongTypeError, from_dict

logger: Logger = logging.getLogger("api")


class BaseReader:
    @staticmethod
    def read_json(location: Path) -> Optional[Any]:
        try:
            with open(location) as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            logger.exception("Unable to locate file")
            return None
        except JSONDecodeError:
            logger.exception("Failed to decode json")
            return None
        except Exception:
            logger.exception(
                "An unhandled exception occurred while reading json from file"
            )
            return None

    @staticmethod
    def dict_to_dataclass(
        dataclass_dict: dict,
        target_dataclass: Any,
        cast_config: list = [],
        strict_config: bool = False,
    ) -> Optional[Any]:
        if not is_dataclass(target_dataclass):
            raise BaseReaderError("{target_dataclass} is not a dataclass")
        try:
            generated_dataclass = from_dict(
                data_class=target_dataclass,
                data=dataclass_dict,
                config=Config(cast=cast_config, strict=strict_config),
            )
            return generated_dataclass
        except WrongTypeError as e:
            raise BaseReaderError(
                "A type of a input value does not"
                "match with a type of a data class field"
            ) from e
        except MissingValueError as e:
            raise BaseReaderError("A value for a required field is not provided") from e
        except ValueError as e:
            raise BaseReaderError from e
        except Exception as e:
            raise BaseReaderError("Datastruct does not match expected struct") from e


class BaseReaderError(Exception):
    pass
