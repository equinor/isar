from enum import Enum
from typing import Literal, Type
from uuid import uuid4

from alitra import Pose, Position
from pydantic import BaseModel, Field, model_validator

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.inspection.inspection import (
    AcousticMeasurement,
    Audio,
    CO2Measurement,
    Image,
    Inspection,
    ThermalImage,
    ThermalVideo,
    Video,
)
from robot_interface.models.mission.status import TaskStatus


class TaskTypes(str, Enum):
    ReturnToHome = "return_to_home"
    TakeImage = "take_image"
    TakeThermalImage = "take_thermal_image"
    TakeVideo = "take_video"
    TakeThermalVideo = "take_thermal_video"
    TakeCO2Measurement = "take_co2_measurement"
    TakeAcousticMeasurement = "take_acoustic_measurement"
    RecordAudio = "record_audio"


class AcousticDetectionType(str, Enum):
    leak = "leak"


# Upper bound (Hz) for the acoustic detection frequency range. Chosen to cover
# the ultrasonic band targeted by leak detection on currently supported robots.
MAX_ACOUSTIC_FREQUENCY_HZ = 100_000


class ZoomDescription(BaseModel):
    objectWidth: float
    objectHeight: float


class Task(BaseModel):
    status: TaskStatus = Field(default=TaskStatus.NotStarted)
    error_message: ErrorMessage | None = Field(default=None)
    tag_id: str | None = Field(default=None)
    id: str = Field(default_factory=lambda: str(uuid4()), frozen=True)


class InspectionTask(Task):
    """
    Base class for all inspection tasks which produce results to be uploaded.
    """

    inspection_id: str = Field(default_factory=lambda: str(uuid4()), frozen=True)
    robot_pose: Pose = Field()
    inspection_description: str | None = Field(default=None)
    zoom: ZoomDescription | None = Field(default=None)
    analysis_types: list[str] | None = Field(default=None)

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Inspection


class ReturnToHome(Task):
    """
    Task which cases the robot to return home
    """

    type: Literal[TaskTypes.ReturnToHome] = TaskTypes.ReturnToHome


class TakeImage(InspectionTask):
    """
    Task which causes the robot to take an image towards the given target.
    """

    target: Position = Field()
    type: Literal[TaskTypes.TakeImage] = TaskTypes.TakeImage

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Image


class TakeThermalImage(InspectionTask):
    """
    Task which causes the robot to take a thermal image towards the given target.
    """

    target: Position = Field()
    type: Literal[TaskTypes.TakeThermalImage] = TaskTypes.TakeThermalImage

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalImage


class TakeVideo(InspectionTask):
    """
    Task which causes the robot to take a video towards the given target.

    Duration of video is given in seconds.
    """

    target: Position = Field()
    duration: float = Field()
    type: Literal[TaskTypes.TakeVideo] = TaskTypes.TakeVideo

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Video


class TakeThermalVideo(InspectionTask):
    """
    Task which causes the robot to record thermal video towards the given target

    Duration of video is given in seconds.
    """

    target: Position = Field()
    duration: float = Field()
    type: Literal[TaskTypes.TakeThermalVideo] = TaskTypes.TakeThermalVideo

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalVideo


class RecordAudio(InspectionTask):
    """
    Task which causes the robot to record a video at its position, facing the target.

    Duration of audio is given in seconds.
    """

    target: Position = Field()
    duration: float = Field()
    type: Literal[TaskTypes.RecordAudio] = TaskTypes.RecordAudio

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Audio


class TakeCO2Measurement(InspectionTask):
    """
    Task which causes the robot to take a CO2 measurement at its position.
    """

    type: Literal[TaskTypes.TakeCO2Measurement] = TaskTypes.TakeCO2Measurement

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return CO2Measurement


class TakeAcousticMeasurement(InspectionTask):
    """
    Task which causes the robot to take an acoustic measurement towards the given target.
    """

    target: Position = Field()
    frequency_from: float = Field()
    frequency_to: float = Field()
    snr_value_threshold: float = Field()
    detection_type: AcousticDetectionType = Field()
    type: Literal[TaskTypes.TakeAcousticMeasurement] = TaskTypes.TakeAcousticMeasurement

    @model_validator(mode="after")
    def _validate_frequency_range(self) -> "TakeAcousticMeasurement":
        if (
            not 0
            <= self.frequency_from
            < self.frequency_to
            <= MAX_ACOUSTIC_FREQUENCY_HZ
        ):
            raise ValueError(
                "Acoustic frequency range must satisfy "
                f"0 <= frequency_from < frequency_to <= {MAX_ACOUSTIC_FREQUENCY_HZ}"
            )
        return self

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return AcousticMeasurement


TASKS = (
    ReturnToHome
    | TakeImage
    | TakeThermalImage
    | TakeVideo
    | TakeThermalVideo
    | TakeCO2Measurement
    | TakeAcousticMeasurement
    | RecordAudio
)
