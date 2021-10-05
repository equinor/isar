from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

from models.geometry.pose import Pose


@dataclass
class TimeIndexedPose:
    pose: Pose
    time: datetime


@dataclass
class InspectionMetadata(ABC):
    start_time: datetime
    time_indexed_pose: Union[TimeIndexedPose, List[TimeIndexedPose]]
    file_type: str
    tag_id: Optional[str] = None
    additional: dict = None
