from abc import ABC
from alitra import Pose
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Type


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

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return InspectionMetadata


class InspectionValue(Inspection):
    value: float = Field(frozen=True)
    unit: str = Field(frozen=True)


class InspectionBlob(Inspection):
    data: Optional[bytes] = Field(default=None, frozen=True)


class Image(InspectionBlob):
    metadata: ImageMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ImageMetadata


class ThermalImage(InspectionBlob):
    metadata: ThermalImageMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalImageMetadata


class Video(InspectionBlob):
    metadata: VideoMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return VideoMetadata


class ThermalVideo(InspectionBlob):
    metadata: ThermalVideoMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalVideoMetadata


class Audio(InspectionBlob):
    metadata: AudioMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return AudioMetadata


class GasMeasurement(InspectionValue):
    metadata: GasMeasurementMetadata

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return GasMeasurementMetadata


class CO2Measurement(GasMeasurement):
    pass
