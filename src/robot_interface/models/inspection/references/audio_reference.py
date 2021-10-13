from dataclasses import dataclass

from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.inspection.metadata import AudioMetadata


@dataclass
class AudioReference(Inspection):
    metadata: AudioMetadata
