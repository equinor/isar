import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import numpy as np

from robot_interface.models.geometry.orientation import Orientation


class JsonService:
    """
    Contains helper functions and custom encoders for handling Json objects.
    """

    @staticmethod
    def to_object(json_string: str) -> SimpleNamespace:
        return json.loads(json_string, object_hook=lambda d: SimpleNamespace(**d))


class EnhancedJSONEncoder(json.JSONEncoder):
    """
    Custom JSONEncoder used in this project. Of special note is the ability to encode dataclasses.
    """

    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, Orientation):
            return o.__dict__
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)
