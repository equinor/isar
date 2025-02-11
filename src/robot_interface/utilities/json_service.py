import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Iterator
from uuid import UUID

import numpy as np
from alitra import Orientation


class EnhancedJSONEncoder(json.JSONEncoder):
    """
    Custom JSONEncoder with the ability to encode dataclasses.
    """

    def default(self, o):
        if is_dataclass(o):
            return asdict(o)  # type: ignore
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, Orientation):
            return o.__dict__
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        if isinstance(o, bytes):
            return "<<non-serializable: bytes>>"
        if isinstance(o, Iterator):
            return "<<non-serializable: iterator>>"
        return super().default(o)
