from dataclasses import dataclass, field
from typing import Iterator, List, Literal, Optional, Type

from alitra import Pose, Position

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.inspection import (
    Audio,
    Image,
    Inspection,
    ThermalImage,
    ThermalVideo,
    Video,
)
from robot_interface.models.mission.status import TaskStatus
from robot_interface.utilities.uuid_string_factory import uuid4_string


@dataclass
class Task:
    status: TaskStatus = field(default=TaskStatus.NotStarted, init=False)
    error_message: Optional[ErrorMessage] = field(default=None, init=False)
    tag_id: Optional[str] = field(default=None)
    id: str = field(default_factory=uuid4_string, init=True)
    _iterator: Iterator = None

    def is_finished(self) -> bool:
        if (
            self.status == TaskStatus.Successful
            or self.status == TaskStatus.PartiallySuccessful
            or self.status == TaskStatus.Cancelled
        ):
            return True
        return False

    def update_task_status(self) -> None:
        return self.status


@dataclass
class InspectionTask(Task):
    """
    Base class for all inspection tasks which produce results to be uploaded.
    """

    inspection: Inspection = field(default=None, init=True)
    tag_id: Optional[str] = field(default=None, init=True)
    robot_pose: Pose = field(default=None, init=True)
    metadata: Optional[dict] = field(default_factory=dict, init=True)

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Inspection


@dataclass
class DockingProcedure(Task):
    """
    Task which causes the robot to dock or undock
    """

    behavior: Literal["dock", "undock"] = field(default=None, init=True)
    type: Literal["docking_procedure"] = "docking_procedure"


@dataclass
class ReturnToHome(Task):
    """
    Task which cases the robot to return home
    """

    pose: Pose = field(default=None, init=True)
    type: Literal["return_to_home"] = "return_to_home"


@dataclass
class Localize(Task):
    """
    Task which causes the robot to localize
    """

    localization_pose: Pose = field(default=None, init=True)
    type: Literal["localize"] = "localize"


@dataclass
class MoveArm(Task):
    """
    Task which causes the robot to move its arm
    """

    arm_pose: str = field(default=None, init=True)
    type: Literal["move_arm"] = "move_arm"


@dataclass
class TakeImage(InspectionTask):
    """
    Task which causes the robot to take an image towards the given coordinate.
    """

    target: Position = field(default=None, init=True)
    type: Literal["take_image"] = "take_image"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Image


@dataclass
class TakeThermalImage(InspectionTask):
    """
    Task which causes the robot to take a thermal image towards the given coordinate.
    """

    target: Position = field(default=None, init=True)
    type: Literal["take_thermal_image"] = "take_thermal_image"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalImage


@dataclass
class TakeVideo(InspectionTask):
    """
    Task which causes the robot to take a video towards the given coordinate.

    Duration of video is given in seconds.
    """

    target: Position = field(default=None, init=True)
    duration: float = field(default=None, init=True)
    type: Literal["take_video"] = "take_video"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Video


@dataclass
class TakeThermalVideo(InspectionTask):
    """
    Task which causes the robot to record thermal video towards the given coordinate

    Duration of video is given in seconds.
    """

    target: Position = field(default=None, init=True)
    duration: float = field(default=None, init=True)
    type: Literal["take_thermal_video"] = "take_thermal_video"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalVideo


@dataclass
class RecordAudio(InspectionTask):
    """
    Task which causes the robot to record a video at its position, facing the target.

    Duration of audio is given in seconds.
    """

    target: Position = field(default=None, init=True)
    duration: float = field(default=None, init=True)
    type: Literal["record_audio"] = "record_audio"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Audio
