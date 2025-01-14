from dataclasses import dataclass
from enum import Enum


class MediaConnectionType(str, Enum):
    LiveKit = "LiveKit"


@dataclass
class MediaConfig:
    url: str
    token: str
    media_connection_type: MediaConnectionType
