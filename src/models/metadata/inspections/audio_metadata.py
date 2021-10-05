from dataclasses import dataclass
from typing import List

from models.metadata.inspection_metadata import InspectionMetadata, TimeIndexedPose


@dataclass
class AudioMetadata(InspectionMetadata):
    time_indexed_pose: List[TimeIndexedPose]
