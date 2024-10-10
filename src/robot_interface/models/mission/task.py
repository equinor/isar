from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Literal, Optional, Type, Union

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


class TaskTypes(str, Enum):
    ReturnToHome = "return_to_home"
    Localize = "localize"
    MoveArm = "move_arm"
    TakeImage = "take_image"
    TakeThermalImage = "take_thermal_image"
    TakeVideo = "take_video"
    TakeThermalVideo = "take_thermal_video"
    RecordAudio = "record_audio"
    DockingProcedure = "docking_procedure"


@dataclass
class Task:
    status: TaskStatus = field(default=TaskStatus.NotStarted, init=False)
    error_message: Optional[ErrorMessage] = field(default=None, init=False)
    tag_id: Optional[str] = field(default=None)
    id: str = field(default_factory=uuid4_string, init=True)

    def is_finished(self) -> bool:
        if (
            self.status == TaskStatus.Successful
            or self.status == TaskStatus.PartiallySuccessful
            or self.status == TaskStatus.Cancelled
            or self.status == TaskStatus.Failed
        ):
            return True
        return False

    def update_task_status(self) -> TaskStatus:
        return self.status


@dataclass
class InspectionTask(Task):
    """
    Base class for all inspection tasks which produce results to be uploaded.
    """

    inspection: Inspection = field(default=None, init=True)
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
    type: Literal[TaskTypes.DockingProcedure] = TaskTypes.DockingProcedure


@dataclass
class ReturnToHome(Task):
    """
    Task which cases the robot to return home
    """

    pose: Pose = field(default=None, init=True)
    type: Literal[TaskTypes.ReturnToHome] = TaskTypes.ReturnToHome


@dataclass
class Localize(Task):
    """
    Task which causes the robot to localize
    """

    localization_pose: Pose = field(default=None, init=True)
    type: Literal[TaskTypes.Localize] = TaskTypes.Localize


@dataclass
class MoveArm(Task):
    """
    Task which causes the robot to move its arm
    """

    arm_pose: str = field(default=None, init=True)
    type: Literal[TaskTypes.MoveArm] = TaskTypes.MoveArm


@dataclass
class TakeImage(InspectionTask):
    """
    Task which causes the robot to take an image towards the given coordinate.
    """

    target: Position = field(default=None, init=True)
    type: Literal[TaskTypes.TakeImage] = TaskTypes.TakeImage

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Image


@dataclass
class TakeThermalImage(InspectionTask):
    """
    Task which causes the robot to take a thermal image towards the given coordinate.
    """

    target: Position = field(default=None, init=True)
    type: Literal[TaskTypes.TakeThermalImage] = TaskTypes.TakeThermalImage

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
    type: Literal[TaskTypes.TakeVideo] = TaskTypes.TakeVideo

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
    type: Literal[TaskTypes.TakeThermalVideo] = TaskTypes.TakeThermalVideo

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
    type: Literal[TaskTypes.RecordAudio] = TaskTypes.RecordAudio

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Audio


TASKS = Union[
    ReturnToHome,
    Localize,
    MoveArm,
    TakeImage,
    TakeThermalImage,
    TakeVideo,
    TakeThermalVideo,
    RecordAudio,
    DockingProcedure,
]
