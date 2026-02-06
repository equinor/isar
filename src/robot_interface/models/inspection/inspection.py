from datetime import datetime
from typing import Optional, Type

from alitra import Pose, Position
from pydantic import BaseModel, Field


class InspectionMetadata(BaseModel):
    start_time: datetime
    robot_pose: Pose
    target_position: Position
    file_type: str
    tag_id: Optional[str] = None
    inspection_description: Optional[str] = None


class ImageMetadata(InspectionMetadata):
    pass


class ThermalImageMetadata(InspectionMetadata):
    pass


class VideoMetadata(InspectionMetadata):
    duration: float


class ThermalVideoMetadata(InspectionMetadata):
    duration: float


class AudioMetadata(InspectionMetadata):
    duration: float


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
    metadata: ImageMetadata  # type: ignore

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ImageMetadata


class ThermalImage(InspectionBlob):
    metadata: ThermalImageMetadata  # type: ignore

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalImageMetadata


class Video(InspectionBlob):
    metadata: VideoMetadata  # type: ignore

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return VideoMetadata


class ThermalVideo(InspectionBlob):
    metadata: ThermalVideoMetadata  # type: ignore

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return ThermalVideoMetadata


class Audio(InspectionBlob):
    metadata: AudioMetadata  # type: ignore

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return AudioMetadata


class GasMeasurement(InspectionValue):
    metadata: GasMeasurementMetadata  # type: ignore

    @staticmethod
    def get_metadata_type() -> Type[InspectionMetadata]:
        return GasMeasurementMetadata


class CO2Measurement(GasMeasurement):
    pass
