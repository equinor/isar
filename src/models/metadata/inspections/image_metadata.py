from dataclasses import dataclass

from models.metadata.inspection_metadata import InspectionMetadata, TimeIndexedPose


@dataclass
class ImageMetadata(InspectionMetadata):
    time_indexed_pose: TimeIndexedPose
