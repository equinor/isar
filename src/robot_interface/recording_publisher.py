"""Optional platform publication boundary for completed recording artifacts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from robot_interface.recording_models import CameraRecording, RecordingSession


@dataclass(frozen=True)
class RecordingArtifact:
    camera_id: str
    artifact_id: str
    path: Path
    content_type: str


class RecordingPublisher(Protocol):
    async def publish_video(self, mission_id: str, artifact: RecordingArtifact) -> str:
        """Upload a completed file and return a stable, opaque artifact reference."""
        ...

    async def publish_session[Camera: CameraRecording](
        self, session: RecordingSession[Camera]
    ) -> None:
        """Publish a status snapshot, translating artifact references for playback."""
        ...
