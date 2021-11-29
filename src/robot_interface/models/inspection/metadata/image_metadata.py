from dataclasses import dataclass

from robot_interface.models.inspection.inspection import (
    InspectionMetadata,
    TimeIndexedPose,
)


@dataclass
class ImageMetadata(InspectionMetadata):
    time_indexed_pose: TimeIndexedPose


@dataclass
class ThermalImageMetadata(InspectionMetadata):
    time_indexed_pose: TimeIndexedPose
