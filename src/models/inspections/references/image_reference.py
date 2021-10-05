from dataclasses import dataclass

from models.inspections.inspection import Inspection
from models.metadata.inspections.image_metadata import ImageMetadata


@dataclass
class ImageReference(Inspection):
    metadata: ImageMetadata


@dataclass
class ThermalImageReference(Inspection):
    metadata: ImageMetadata
