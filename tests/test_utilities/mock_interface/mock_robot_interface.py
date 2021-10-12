from datetime import datetime
import logging
from logging import Logger
from typing import Any, Optional, Tuple, List

from robot_interfaces.robot_interface import RobotInterface

from models.enums.mission_status import MissionStatus
from models.geometry.frame import Frame
from models.geometry.joints import Joints
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


class MockRobot(RobotInterface):
    def __init__(
        self,
        schedule_step: Tuple[bool, Optional[Any], Optional[Joints]] = (True, 1, None),
        mission_scheduled: bool = False,
        mission_status: MissionStatus = MissionStatus.InProgress,
        abort_mission: bool = True,
        pose: Pose = Pose(
            position=Position(x=0, y=0, z=0, frame=Frame.Robot),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame.Robot),
            frame=Frame.Robot,
        ),
    ):
        self.logger: Logger = logging.getLogger()
        self.schedule_step_return_value: Tuple[
            bool, Optional[Any], Optional[Joints]
        ] = schedule_step
        self.mission_scheduled_return_value: bool = mission_scheduled
        self.mission_status_return_value: MissionStatus = mission_status
        self.abort_mission_return_value: bool = abort_mission
        self.robot_pose_return_value: Pose = pose

    def schedule_step(self, step: Step) -> Tuple[bool, Optional[Any], Optional[Joints]]:
        self.logger.info("Mock for schedule_step in scheduler was called")
        return self.schedule_step_return_value

    def mission_scheduled(self) -> bool:
        self.logger.info("Mock for mission_scheduled in scheduler was called")

        return self.mission_scheduled_return_value

    def mission_status(self, mission_id: Any) -> MissionStatus:
        self.logger.info("Mock for mission_status in scheduler was called")
        return self.mission_status_return_value

    def abort_mission(self) -> bool:
        self.logger.info("Mock for abort_mission in scheduler was called")
        return self.abort_mission_return_value

    def log_status(
        self, mission_id: Any, mission_status: MissionStatus, current_step: Step
    ):
        self.logger.info("Mock for log_status in scheduler was called")

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

    def robot_pose(self) -> Pose:
        self.logger.info("Mock for robot_pose in Telemetry was called")
        return self.robot_pose_return_value


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
