import logging
from datetime import datetime
from logging import Logger
from typing import Any, List

from models.geometry.frame import Frame
from models.geometry.orientation import Orientation
from models.geometry.pose import Pose
from models.geometry.position import Position
from models.inspections.formats.image import Image
from models.inspections.inspection import Inspection
from models.inspections.inspection_result import InspectionResult
from models.inspections.references.image_reference import ImageReference
from models.metadata.inspection_metadata import TimeIndexedPose
from models.metadata.inspections.image_metadata import ImageMetadata
from models.planning.step import Step
from robot_interfaces.robot_storage_interface import RobotStorageInterface


def mock_image_metadata() -> ImageMetadata:
    return ImageMetadata(
        datetime.now(),
        TimeIndexedPose(
            Pose(
                Position(0, 0, 0, Frame.Robot),
                Orientation(0, 0, 0, 1, Frame.Robot),
                Frame.Robot,
            ),
            datetime.now(),
        ),
        file_type="jpg",
    )


class MockStorage(RobotStorageInterface):
    def __init__(self):
        self.logger: Logger = logging.getLogger()

    def get_inspection_references(
        self, vendor_mission_id: Any, current_step: Step
    ) -> List[Inspection]:
        self.logger.info("Mock for get_inspection_references in storage was called")
        return [ImageReference(vendor_mission_id, mock_image_metadata())]

    def download_inspection_result(self, inspection: Inspection) -> InspectionResult:
        self.logger.info("Mock for download_inspection_result in storage was called")
        return Image(
            inspection.id,
            mock_image_metadata(),
            b"Some binary image data",
        )
