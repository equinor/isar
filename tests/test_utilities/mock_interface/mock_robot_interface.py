import logging
from datetime import datetime
from logging import Logger
from typing import Any, List, Optional, Tuple

from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.joints import Joints
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.inspection.formats import Image
from robot_interface.models.inspection.inspection import (
    Inspection,
    InspectionResult,
    TimeIndexedPose,
)
from robot_interface.models.inspection.metadata import ImageMetadata
from robot_interface.models.inspection.references import ImageReference
from robot_interface.models.mission import MissionStatus, Step
from robot_interface.robot_interface import RobotInterface


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
