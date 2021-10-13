from dataclasses import dataclass
from typing import List

from robot_interface.models.inspection.inspection import (
    InspectionMetadata,
    TimeIndexedPose,
)


@dataclass
class AudioMetadata(InspectionMetadata):
    time_indexed_pose: List[TimeIndexedPose]
