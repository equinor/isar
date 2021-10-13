from dataclasses import dataclass

from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.inspection.metadata import VideoMetadata


@dataclass
class VideoReference(Inspection):
    metadata: VideoMetadata
