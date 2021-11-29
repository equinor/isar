from dataclasses import dataclass

from robot_interface.models.inspection.inspection import InspectionResult
from robot_interface.models.inspection.metadata.image_metadata import (
    ThermalImageMetadata,
    ImageMetadata,
)


@dataclass
class Image(InspectionResult):
    metadata: ImageMetadata


@dataclass
class ThermalImage(InspectionResult):
    metadata: ThermalImageMetadata
