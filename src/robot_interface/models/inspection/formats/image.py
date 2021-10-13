from dataclasses import dataclass

from robot_interface.models.inspection.inspection import InspectionResult
from robot_interface.models.inspection.metadata import ImageMetadata


@dataclass
class Image(InspectionResult):
    metadata: ImageMetadata


@dataclass
class ThermalImage(InspectionResult):
    metadata: ImageMetadata
