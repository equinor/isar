from enum import Enum

from pydantic import BaseModel, model_validator


class MediaConnectionType(str, Enum):
    LiveKit = "LiveKit"
    OvenMediaEngine = "OvenMediaEngine"


class MediaStream(BaseModel):
    role: str
    url: str


class MediaConfig(BaseModel):
    url: str | None = None
    token: str | None = None
    streams: list[MediaStream] | None = None
    media_connection_type: MediaConnectionType

    @model_validator(mode="after")
    def validate_connection_details(self) -> MediaConfig:
        if self.media_connection_type == MediaConnectionType.LiveKit and (
            self.url is None or self.token is None
        ):
            raise ValueError("LiveKit requires a URL and token")
        if (
            self.media_connection_type == MediaConnectionType.OvenMediaEngine
            and not self.streams
        ):
            raise ValueError("OvenMediaEngine requires at least one stream")
        return self
