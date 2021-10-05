from dataclasses import dataclass

from models.inspections.inspection import Inspection
from models.metadata.inspections.audio_metadata import AudioMetadata


@dataclass
class AudioReference(Inspection):
    metadata: AudioMetadata
