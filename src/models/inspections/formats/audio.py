from dataclasses import dataclass

from models.inspections.inspection_result import InspectionResult
from models.metadata.inspections.audio_metadata import AudioMetadata


@dataclass
class Audio(InspectionResult):
    metadata: AudioMetadata
