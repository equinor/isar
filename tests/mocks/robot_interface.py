from datetime import datetime
from typing import Any, List, Optional, Sequence, Tuple

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
from robot_interface.models.mission import TaskStatus, Task
from robot_interface.robot_interface import RobotInterface


class MockRobot(RobotInterface):
    def __init__(
        self,
        schedule_task: Tuple[bool, Optional[Joints]] = (True, None),
        mission_scheduled: bool = False,
        task_status: TaskStatus = TaskStatus.Completed,
        abort_mission: bool = True,
        pose: Pose = Pose(
            position=Position(x=0, y=0, z=0, frame=Frame.Robot),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame.Robot),
            frame=Frame.Robot,
        ),
    ):
        self.schedule_task_return_value: Tuple[bool, Optional[Joints]] = schedule_task
        self.mission_scheduled_return_value: bool = mission_scheduled
        self.task_status_return_value: TaskStatus = task_status
        self.abort_mission_return_value: bool = abort_mission
        self.robot_pose_return_value: Pose = pose

    def schedule_task(self, task: Task) -> Tuple[bool, Optional[Joints]]:
        return self.schedule_task_return_value

    def mission_scheduled(self) -> bool:
        return self.mission_scheduled_return_value

    def task_status(self, mission_id: Any) -> TaskStatus:
        return self.task_status_return_value

    def abort_mission(self) -> bool:
        return self.abort_mission_return_value

    def log_status(self, task_status: TaskStatus, current_task: Task):
        pass

    def get_inspection_references(self, current_task: Task) -> Sequence[Inspection]:
        return [ImageReference(id=current_task.id, metadata=mock_image_metadata())]  # type: ignore

    def download_inspection_result(self, inspection: Inspection) -> InspectionResult:
        return Image(
            inspection.id,
            mock_image_metadata(),
            b"Some binary image data",
        )

    def robot_pose(self) -> Pose:
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
