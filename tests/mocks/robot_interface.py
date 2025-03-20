from datetime import datetime
from queue import Empty, Queue
from threading import Thread
from typing import Callable, List

from alitra import Frame, Orientation, Pose, Position

from isar.models.communication.queues.status_queue import StatusQueue
from robot_interface.models.exceptions.robot_exceptions import (
    RobotCommunicationException,
)
from robot_interface.models.inspection.inspection import (
    Image,
    ImageMetadata,
    Inspection,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus, TaskStatus
from robot_interface.models.mission.task import InspectionTask, Task
from robot_interface.models.robots.media import MediaConfig, MediaConnectionType
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
        return Image(
            metadata=mock_image_metadata(),
            id=task.inspection_id,
            data=b"Some binary image data",
        )

    def generate_media_config(self) -> MediaConfig:
        return MediaConfig(
            url="mockURL",
            token="mockToken",
            media_connection_type=MediaConnectionType.LiveKit,
        )

    def register_inspection_callback(
        self, callback_function: Callable[[Inspection, Mission], None]
    ) -> None:
        return

    def initialize(self) -> None:
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


class MockRobotOfflineToRobotStandingStillTest(MockRobot):
    def __init__(self, current_state: StatusQueue):
        self.entered_offline = False
        self.current_state = current_state

    def robot_status(self) -> RobotStatus:
        try:
            new_state = self.current_state.check()
            if new_state == "offline":
                self.entered_offline = True
                return RobotStatus.Available

            if not self.entered_offline:
                return RobotStatus.Offline

            return RobotStatus.Available
        except Empty:
            raise RobotCommunicationException("Could not read state machine state")


class MockRobotBlockedProtectiveStopToRobotStandingStillTest(MockRobot):
    def __init__(self, current_state: StatusQueue):
        self.entered_blocked_p_stop = False
        self.current_state = current_state

    def robot_status(self) -> RobotStatus:
        try:
            if self.current_state.check() == "blocked_protective_stop":
                self.entered_blocked_p_stop = True
                return RobotStatus.Available
            if not self.entered_blocked_p_stop:
                return RobotStatus.BlockedProtectiveStop
            return RobotStatus.Available
        except Empty:
            raise RobotCommunicationException("Could not read state machine state")


class MockRobotHomeToRobotStandingStillTest(MockRobot):
    def __init__(self, current_state: StatusQueue):
        self.entered_home = False
        self.current_state = current_state

    def robot_status(self) -> RobotStatus:
        try:
            if self.current_state.check() == "home":
                self.entered_home = True
                return RobotStatus.Available
            if not self.entered_home:
                return RobotStatus.Home
            return RobotStatus.Available
        except Empty:
            raise RobotCommunicationException("Could not read state machine state")


class MockRobotOfflineToHomeTest(MockRobot):
    def __init__(self, current_state: StatusQueue):
        self.entered_offline = False
        self.current_state = current_state

    def robot_status(self) -> RobotStatus:
        try:
            if self.current_state.check() == "offline":
                self.entered_offline = True
                return RobotStatus.Home
            if not self.entered_offline:
                return RobotStatus.Offline
            return RobotStatus.Home
        except Empty:
            raise RobotCommunicationException("Could not read state machine state")
