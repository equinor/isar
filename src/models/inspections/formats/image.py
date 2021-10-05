from dataclasses import dataclass

from models.inspections.inspection_result import InspectionResult
from models.metadata.inspections.image_metadata import ImageMetadata


@dataclass
class Image(InspectionResult):
    metadata: ImageMetadata


@dataclass
class ThermalImage(InspectionResult):
    metadata: ImageMetadata
