from dataclasses import dataclass

from robot_interface.models.inspection.inspection import InspectionResult
from robot_interface.models.inspection.metadata import AudioMetadata


@dataclass
class Audio(InspectionResult):
    metadata: AudioMetadata
