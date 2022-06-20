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
    TimeIndexedPose,
)
from robot_interface.models.mission import InspectionStep, Step, StepStatus
from robot_interface.robot_interface import RobotInterface


class MockRobot(RobotInterface):
    def __init__(
        self,
        initiate_step: bool = True,
        step_status: StepStatus = StepStatus.Successful,
        stop: bool = True,
        pose: Pose = Pose(
            position=Position(x=0, y=0, z=0, frame=Frame("robot")),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame("robot")),
            frame=Frame("robot"),
        ),
    ):
        self.initiate_step_return_value: bool = initiate_step
        self.step_status_return_value: StepStatus = step_status
        self.stop_return_value: bool = stop
        self.robot_pose_return_value: Pose = pose

    def initiate_step(self, step: Step) -> None:
        return

    def step_status(self) -> StepStatus:
        return self.step_status_return_value

    def stop(self) -> None:
        return

    def get_inspections(self, step: InspectionStep) -> Sequence[Inspection]:
        image: Image = Image(mock_image_metadata())
        image.data = b"Some binary image data"
        return [image]

    def initialize(self, params: InitializeParams) -> None:
        return

    def get_telemetry_publishers(self, queue: Queue, robot_id: str) -> List[Thread]:
        return []


def mock_image_metadata() -> ImageMetadata:
    return ImageMetadata(
        datetime.now(),
        TimeIndexedPose(
            Pose(
                Position(0, 0, 0, Frame("robot")),
                Orientation(0, 0, 0, 1, Frame("robot")),
                Frame("robot"),
            ),
            datetime.now(),
        ),
        file_type="jpg",
    )
