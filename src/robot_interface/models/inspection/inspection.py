from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Type

from alitra import Pose
from pydantic import BaseModel, Field


@dataclass
class InspectionMetadata(ABC):
    start_time: datetime
    pose: Pose
    file_type: str
    tag_id: Optional[str] = field(default=None, init=False)
    inspection_description: Optional[str] = field(default=None, init=False)


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
class GasMeasurementMetadata(InspectionMetadata):
    pass


class Inspection(BaseModel):
    metadata: InspectionMetadata
    id: str = Field(frozen=True)
    data: Optional[bytes] = Field(default=None, frozen=True)

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return InspectionMetadata


class Image(Inspection):
    metadata: ImageMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ImageMetadata


class ThermalImage(Inspection):
    metadata: ThermalImageMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalImageMetadata


class Video(Inspection):
    metadata: VideoMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return VideoMetadata


class ThermalVideo(Inspection):
    metadata: ThermalVideoMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalVideoMetadata


class Audio(Inspection):
    metadata: AudioMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return AudioMetadata


class GasMeasurement(Inspection):
    metadata: GasMeasurementMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return GasMeasurementMetadata
