from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Type

from alitra import Pose

from robot_interface.utilities.uuid_string_factory import uuid4_string


@dataclass
class InspectionMetadata(ABC):
    start_time: datetime
    pose: Pose
    file_type: str
    analysis_type: Optional[str] = field(default=None, init=False)
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
class AudioMetadata(InspectionMetadata):
    duration: Optional[float] = field(default=None)


@dataclass
class Inspection:
    metadata: InspectionMetadata
    id: str = field(default_factory=uuid4_string, init=True)
    data: Optional[bytes] = field(default=None, init=False)

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return InspectionMetadata


@dataclass
class Image(Inspection):
    metadata: ImageMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ImageMetadata


@dataclass
class ThermalImage(Inspection):
    metadata: ThermalImageMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalImageMetadata


@dataclass
class Video(Inspection):
    metadata: VideoMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return VideoMetadata


@dataclass
class ThermalVideo(Inspection):
    metadata: ThermalVideoMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalVideoMetadata


@dataclass
class Audio(Inspection):
    metadata: AudioMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return AudioMetadata
