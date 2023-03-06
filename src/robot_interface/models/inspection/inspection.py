from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Type
from uuid import UUID, uuid4

from alitra import Pose


@dataclass
class TimeIndexedPose:
    pose: Pose
    time: datetime


@dataclass
class InspectionMetadata(ABC):
    start_time: datetime
    time_indexed_pose: TimeIndexedPose
    file_type: str
    analysis: Optional[List] = field(default_factory=list, init=False)
    tag_id: Optional[str] = field(default=None, init=False)
    additional: Optional[dict] = field(default_factory=dict, init=False)


@dataclass
class ImageMetadata(InspectionMetadata):
    pass


@dataclass
class ThermalImageMetadata(InspectionMetadata):
    pass


@dataclass
class VideoMetadata(InspectionMetadata):
    duration: Optional[float] = field(default=None)


@dataclass
class ThermalVideoMetadata(InspectionMetadata):
    duration: Optional[float] = field(default=None)


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


@dataclass
class Video(Inspection):
    metadata: VideoMetadata


@dataclass
class ThermalVideo(Inspection):
    metadata: ThermalVideoMetadata
