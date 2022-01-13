from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from robot_interface.models.geometry.pose import Pose


@dataclass
class TimeIndexedPose:
    pose: Pose
    time: datetime


@dataclass
class InspectionMetadata(ABC):
    start_time: datetime
    time_indexed_pose: TimeIndexedPose
    file_type: str
    tag_id: Optional[str] = field(default=None, init=False)
    additional: Optional[dict] = field(default=None, init=False)


@dataclass
class ImageMetadata(InspectionMetadata):
    pass


@dataclass
class ThermalImageMetadata(InspectionMetadata):
    pass


@dataclass
class Inspection:
    id: UUID = field(default_factory=uuid4, init=False)
    metadata: InspectionMetadata
    data: Optional[bytes] = field(default=None, init=False)


@dataclass
class Image(Inspection):
    metadata: ImageMetadata


@dataclass
class ThermalImage(Inspection):
    metadata: ThermalImageMetadata
