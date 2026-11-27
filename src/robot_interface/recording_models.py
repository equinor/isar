"""Typed recording publication snapshots, independent of capture implementation."""

from typing import Literal

from alitra import Pose
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


class RecordingPosition(RecordingModel):
    x: float
    y: float
    z: float


class RecordingOrientation(RecordingModel):
    x: float
    y: float
    z: float
    w: float


class RecordingPose(RecordingModel):
    position: RecordingPosition
    orientation: RecordingOrientation
    frame: str = "asset"

    @classmethod
    def from_alitra(cls, pose: Pose) -> RecordingPose:
        return cls(
            position=RecordingPosition(
                x=float(pose.position.x),
                y=float(pose.position.y),
                z=float(pose.position.z),
            ),
            orientation=RecordingOrientation(
                x=float(pose.orientation.x),
                y=float(pose.orientation.y),
                z=float(pose.orientation.z),
                w=float(pose.orientation.w),
            ),
            frame=pose.frame.name,
        )


class PoseSample(RecordingModel):
    received_at: str
    pose: RecordingPose
    source_timestamp: str | None = None
    map_name: str | None = None
    confidence: float | None = None


class SegmentTiming(RecordingModel):
    segment_index: int
    video_start_seconds: float
    duration_seconds: float
    capture_start_at: str | None = None


class CameraRecording(RecordingModel):
    camera_id: str
    key: str
    status: CameraStatus
    artifact_reference: str | None = None
    # Older durable catalogs contain the published blob name directly.
    blob_name: str | None = None
    segment_timings: list[SegmentTiming] | None = None
    error: str | None = None


class RecordingSession[Camera: CameraRecording](RecordingModel):
    run_id: str
    status: SessionStatus
    cameras: dict[str, Camera]
    mission_name: str | None = None
    gaps: list[RecordingGap] = Field(default_factory=list)
    pose_samples: list[PoseSample] | None = None
    isar_id: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    error: str | None = None
