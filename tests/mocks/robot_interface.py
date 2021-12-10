from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.inspection.inspection import (
    Image,
    ImageMetadata,
    Inspection,
    TimeIndexedPose,
)
from robot_interface.models.mission import Task, TaskStatus
from robot_interface.robot_interface import RobotInterface


class MockRobot(RobotInterface):
    def __init__(
        self,
        schedule_task: bool = True,
        mission_scheduled: bool = False,
        task_status: TaskStatus = TaskStatus.Completed,
        abort_mission: bool = True,
        pose: Pose = Pose(
            position=Position(x=0, y=0, z=0, frame=Frame.Robot),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame.Robot),
            frame=Frame.Robot,
        ),
    ):
        self.schedule_task_return_value: bool = schedule_task
        self.mission_scheduled_return_value: bool = mission_scheduled
        self.task_status_return_value: TaskStatus = task_status
        self.abort_mission_return_value: bool = abort_mission
        self.robot_pose_return_value: Pose = pose

    def schedule_task(self, task: Task) -> bool:
        return self.schedule_task_return_value

    def mission_scheduled(self) -> bool:
        return self.mission_scheduled_return_value

    def task_status(self, task_id: Optional[UUID]) -> TaskStatus:
        return self.task_status_return_value

    def abort_mission(self) -> bool:
        return self.abort_mission_return_value

    def log_status(self, task_status: TaskStatus, current_task: Task):
        pass

    def get_inspection_references(self, current_task: Task) -> Sequence[Inspection]:
        return [Image(metadata=mock_image_metadata())]

    def download_inspection_result(self, inspection: Inspection) -> Inspection:
        image: Image = Image(mock_image_metadata())
        image.data = b"Some binary image data"
        return image

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
