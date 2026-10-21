"""Typed recording publication snapshots, independent of capture implementation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SessionStatus = Literal[
    "Starting", "Recording", "Reconnecting", "Processing", "Ready", "Failed", "Expired"
]
CameraStatus = Literal["Recording", "Processing", "Ready", "Failed", "Expired"]


class RecordingModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        validate_assignment=True,
        extra="allow",
    )


class RecordingGap(RecordingModel):
    at: str
    reason: str


class CameraRecording(RecordingModel):
    camera_id: str
    key: str
    status: CameraStatus
    artifact_reference: str | None = None
    # Older durable catalogs contain the published blob name directly.
    blob_name: str | None = None
    error: str | None = None


class RecordingSession[Camera: CameraRecording](RecordingModel):
    run_id: str
    status: SessionStatus
    cameras: dict[str, Camera]
    gaps: list[RecordingGap] = Field(default_factory=list)
    isar_id: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    error: str | None = None
