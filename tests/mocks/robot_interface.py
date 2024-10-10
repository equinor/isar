from dataclasses import field
from datetime import datetime
from queue import Queue
from threading import Thread
from typing import List, Sequence

from alitra import Frame, Orientation, Pose, Position

from robot_interface.models.initialize import InitializeParams
from robot_interface.models.inspection.inspection import (
    Image,
    ImageMetadata,
    Inspection,
)
from robot_interface.models.mission.mission import Mission

from robot_interface.models.mission.status import MissionStatus, RobotStatus, TaskStatus
from robot_interface.models.mission.task import InspectionTask, Task
from robot_interface.robot_interface import RobotInterface


class MockRobot(RobotInterface):

    def __init__(
        self,
        mission_status: MissionStatus = MissionStatus.Successful,
        task_status: TaskStatus = TaskStatus.Successful,
        stop: bool = True,
        pose: Pose = Pose(
            position=Position(x=0, y=0, z=0, frame=Frame("robot")),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame("robot")),
            frame=Frame("robot"),
        ),
        robot_status: RobotStatus = RobotStatus.Available,
    ):
        self.mission_status_return_value: MissionStatus = mission_status
        self.task_status_return_value: TaskStatus = task_status
        self.stop_return_value: bool = stop
        self.robot_pose_return_value: Pose = pose
        self.robot_status_return_value: RobotStatus = robot_status

    def initiate_mission(self, mission: Mission) -> None:
        return

    def initiate_task(self, task: Task) -> None:
        return

    def task_status(self, task_id: str) -> TaskStatus:
        return self.task_status_return_value

    def stop(self) -> None:
        return

    def pause(self) -> None:
        return

    def resume(self) -> None:
        return

    def get_inspection(self, task: InspectionTask) -> Inspection:
        image: Image = Image(mock_image_metadata())
        image.data = b"Some binary image data"
        return image

    def initialize(self, params: InitializeParams) -> None:
        return

    def get_telemetry_publishers(
        self, queue: Queue, isar_id: str, robot_name: str
    ) -> List[Thread]:
        return []

    def robot_status(self) -> RobotStatus:
        return self.robot_status_return_value


def mock_image_metadata() -> ImageMetadata:
    return ImageMetadata(
        start_time=datetime.now(),
        pose=Pose(
            Position(0, 0, 0, Frame("robot")),
            Orientation(0, 0, 0, 1, Frame("robot")),
            Frame("robot"),
        ),
        file_type="jpg",
    )


class MockRobotIdleToOfflineToIdleTest(MockRobot):
    def __init__(self):
        self.first = True

    def robot_status(self) -> RobotStatus:
        if self.first:
            self.first = False
            return RobotStatus.Offline

        return RobotStatus.Available
