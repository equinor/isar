import time
from datetime import datetime
from queue import Queue
from threading import Thread
from typing import Callable, List, Optional

from alitra import Frame, Orientation, Pose, Position

from isar.models.events import Event
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
from robot_interface.models.mission.task import InspectionTask
from robot_interface.models.robots.media import MediaConfig, MediaConnectionType
from robot_interface.robot_interface import RobotInterface


class StubRobot(RobotInterface):
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
        initiate_mission_delay: float = 0.0,
    ):
        self.mission_status_return_value: MissionStatus = mission_status
        self.task_status_return_value: TaskStatus = task_status
        self.stop_return_value: bool = stop
        self.robot_pose_return_value: Pose = pose
        self.robot_status_return_value: RobotStatus = robot_status
        self.initiate_mission_delay: float = initiate_mission_delay
        self.mission: Optional[Mission] = None

    def initiate_mission(self, mission: Mission) -> None:
        time.sleep(self.initiate_mission_delay)
        self.mission = mission
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
            metadata=stub_image_metadata(),
            id=task.inspection_id,
            data=b"Some binary image data",
        )

    def generate_media_config(self) -> MediaConfig:
        return MediaConfig(
            url="stubURL",
            token="stubToken",
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

    def get_battery_level(self):
        return 80.0


def stub_image_metadata() -> ImageMetadata:
    return ImageMetadata(
        start_time=datetime.now(),
        robot_pose=Pose(
            Position(0, 0, 0, Frame("robot")),
            Orientation(0, 0, 0, 1, Frame("robot")),
            Frame("robot"),
        ),
        target_position=Position(0, 0, 0, Frame("robot")),
        file_type="jpg",
    )


class StubRobotOfflineToAvailableTest(StubRobot):
    def __init__(self, current_state: Event):
        self.entered_offline = False
        self.current_state = current_state

    def robot_status(self) -> RobotStatus:
        new_state = self.current_state.check()
        if new_state is None:
            raise RobotCommunicationException("Could not read state machine state")
        if new_state == "offline":
            self.entered_offline = True
            return RobotStatus.Available

        if not self.entered_offline:
            return RobotStatus.Offline

        return RobotStatus.Available


class StubRobotBlockedProtectiveStopToHomeTest(StubRobot):
    def __init__(self, current_state: Event):
        self.entered_blocked_p_stop = False
        self.current_state = current_state

    def robot_status(self) -> RobotStatus:
        current_state = self.current_state.check()
        if current_state is None:
            raise RobotCommunicationException("Could not read state machine state")
        if current_state == "blocked_protective_stop":
            self.entered_blocked_p_stop = True
            return RobotStatus.Available
        if not self.entered_blocked_p_stop:
            return RobotStatus.BlockedProtectiveStop
        return RobotStatus.Available


class StubRobotOfflineToHomeTest(StubRobot):
    def __init__(self, current_state: Event):
        self.entered_offline = False
        self.current_state = current_state

    def robot_status(self) -> RobotStatus:
        current_state = self.current_state.check()
        if current_state is None:
            raise RobotCommunicationException("Could not read state machine state")
        if current_state == "offline":
            self.entered_offline = True
            return RobotStatus.Home
        if not self.entered_offline:
            return RobotStatus.Offline
        return RobotStatus.Home


class StubRobotRobotStatusBusyIfNotHomeOrUnknownStatus(StubRobot):
    def __init__(
        self,
        current_state: Event,
        initiate_mission_delay: float = 0.0,
    ):
        super().__init__()
        self.current_state = current_state
        self.initiate_mission_delay: float = initiate_mission_delay
        self.return_home_mission_just_finished_successfully = False

    def task_status(self, task_id: str) -> TaskStatus:
        if self.mission._is_return_to_home_mission():
            if self.task_status_return_value == TaskStatus.Successful:
                self.return_home_mission_just_finished_successfully = True
        return self.task_status_return_value

    def robot_status(self) -> RobotStatus:
        current_state = self.current_state.check()
        if current_state is None:
            raise RobotCommunicationException("Could not read state machine state")
        if current_state == "home":
            return RobotStatus.Home
        elif current_state == "unknown_status":
            return RobotStatus.Home
        elif self.return_home_mission_just_finished_successfully:
            return RobotStatus.Home

        return RobotStatus.Busy
