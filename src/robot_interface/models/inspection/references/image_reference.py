from dataclasses import dataclass

from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.inspection.metadata import ImageMetadata


@dataclass
class ImageReference(Inspection):
    metadata: ImageMetadata


@dataclass
class ThermalImageReference(Inspection):
    metadata: ImageMetadata
