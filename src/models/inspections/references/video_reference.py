from dataclasses import dataclass

from models.inspections.inspection import Inspection
from models.metadata.inspections.video_metadata import VideoMetadata


@dataclass
class VideoReference(Inspection):
    metadata: VideoMetadata
