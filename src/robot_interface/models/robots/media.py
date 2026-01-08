from enum import Enum

from pydantic import BaseModel


class MediaConnectionType(str, Enum):
    LiveKit = "LiveKit"


class MediaConfig(BaseModel):
    url: str
    token: str
    media_connection_type: MediaConnectionType
