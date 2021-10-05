from dataclasses import dataclass

from models.inspections.inspection_result import InspectionResult
from models.metadata.inspections.video_metadata import VideoMetadata


@dataclass
class Video(InspectionResult):
    metadata: VideoMetadata
