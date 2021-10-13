from dataclasses import dataclass

from robot_interface.models.inspection.inspection import InspectionResult
from robot_interface.models.inspection.metadata import VideoMetadata


@dataclass
class Video(InspectionResult):
    metadata: VideoMetadata
