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
from robot_interface.models.mission import InspectionTask, Task, TaskStatus
from robot_interface.robot_interface import RobotInterface


class MockRobot(RobotInterface):
    def __init__(
        self,
        initiate_task: bool = True,
        task_status: TaskStatus = TaskStatus.Completed,
        stop: bool = True,
        pose: Pose = Pose(
            position=Position(x=0, y=0, z=0, frame=Frame.Robot),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame.Robot),
            frame=Frame.Robot,
        ),
    ):
        self.initiate_task_return_value: bool = initiate_task
        self.task_status_return_value: TaskStatus = task_status
        self.stop_return_value: bool = stop
        self.robot_pose_return_value: Pose = pose

    def initiate_task(self, task: Task) -> None:
        return

    def task_status(self) -> TaskStatus:
        return self.task_status_return_value

    def stop(self) -> None:
        return

    def get_inspections(self, task: InspectionTask) -> Sequence[Inspection]:
        image: Image = Image(mock_image_metadata())
        image.data = b"Some binary image data"
        return [image]


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
