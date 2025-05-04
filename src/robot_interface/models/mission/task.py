from enum import Enum
from typing import Literal, Optional, Type, Union

from alitra import Pose, Position
from pydantic import BaseModel, Field

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.inspection.inspection import (
    Audio,
    GasMeasurement,
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
    MoveArm = "move_arm"
    TakeImage = "take_image"
    TakeThermalImage = "take_thermal_image"
    TakeVideo = "take_video"
    TakeThermalVideo = "take_thermal_video"
    TakeGasMeasurement = "take_gas_measurement"
    RecordAudio = "record_audio"


class ZoomDescription(BaseModel):
    objectWidth: float
    objectHeight: float


class Task(BaseModel):
    status: TaskStatus = Field(default=TaskStatus.NotStarted)
    error_message: Optional[ErrorMessage] = Field(default=None)
    tag_id: Optional[str] = Field(default=None)
    id: str = Field(default_factory=uuid4_string, frozen=True)

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


class InspectionTask(Task):
    """
    Base class for all inspection tasks which produce results to be uploaded.
    """

    inspection_id: str = Field(default_factory=uuid4_string, frozen=True)
    robot_pose: Pose = Field(default=None, init=True)
    inspection_description: Optional[str] = Field(default=None)
    zoom: Optional[ZoomDescription] = Field(default=None)

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Inspection


class ReturnToHome(Task):
    """
    Task which cases the robot to return home
    """

    type: Literal[TaskTypes.ReturnToHome] = TaskTypes.ReturnToHome


class MoveArm(Task):
    """
    Task which causes the robot to move its arm
    """

    arm_pose: str = Field(default=None)
    type: Literal[TaskTypes.MoveArm] = TaskTypes.MoveArm


class TakeImage(InspectionTask):
    """
    Task which causes the robot to take an image towards the given target.
    """

    target: Position = Field(default=None)
    type: Literal[TaskTypes.TakeImage] = TaskTypes.TakeImage

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Image


class TakeThermalImage(InspectionTask):
    """
    Task which causes the robot to take a thermal image towards the given target.
    """

    target: Position = Field(default=None)
    type: Literal[TaskTypes.TakeThermalImage] = TaskTypes.TakeThermalImage

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalImage


class TakeVideo(InspectionTask):
    """
    Task which causes the robot to take a video towards the given target.

    Duration of video is given in seconds.
    """

    target: Position = Field(default=None)
    duration: float = Field(default=None)
    type: Literal[TaskTypes.TakeVideo] = TaskTypes.TakeVideo

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Video


class TakeThermalVideo(InspectionTask):
    """
    Task which causes the robot to record thermal video towards the given target

    Duration of video is given in seconds.
    """

    target: Position = Field(default=None)
    duration: float = Field(default=None)
    type: Literal[TaskTypes.TakeThermalVideo] = TaskTypes.TakeThermalVideo

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalVideo


class RecordAudio(InspectionTask):
    """
    Task which causes the robot to record a video at its position, facing the target.

    Duration of audio is given in seconds.
    """

    target: Position = Field(default=None)
    duration: float = Field(default=None)
    type: Literal[TaskTypes.RecordAudio] = TaskTypes.RecordAudio

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Audio


class TakeGasMeasurement(InspectionTask):
    """
    Task which causes the robot to take a CO2 measurement at its position.

    Duration of audio is given in seconds.
    """

    type: Literal[TaskTypes.TakeGasMeasurement] = TaskTypes.TakeGasMeasurement

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return GasMeasurement


TASKS = Union[
    ReturnToHome,
    MoveArm,
    TakeImage,
    TakeThermalImage,
    TakeVideo,
    TakeThermalVideo,
    TakeGasMeasurement,
    RecordAudio,
]
