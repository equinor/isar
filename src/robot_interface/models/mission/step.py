from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional, Type, Union
from uuid import UUID, uuid4

from alitra import Pose, Position

from robot_interface.models.inspection.inspection import (
    Image,
    Inspection,
    ThermalImage,
    ThermalVideo,
    Video,
)
from robot_interface.models.mission.status import StepStatus


@dataclass
class Step:
    """
    Base class for all steps in a mission.
    """

    id: UUID = field(default_factory=uuid4, init=False)
    status: StepStatus = field(default=StepStatus.NotStarted, init=False)

    def __str__(self):
        def add_indent(text: str) -> str:
            return "".join("  " + line for line in text.splitlines(True))

        def robot_class_to_pretty_string(obj: Step) -> str:
            log_message: str = ""
            for attr in dir(obj):
                if callable(getattr(obj, attr)) or attr.startswith("__"):
                    continue

                value: Any = getattr(obj, attr)
                try:
                    package_name: Optional[str] = (
                        str(value.__class__).split("'")[1].split(".")[0]
                    )
                except (AttributeError, IndexError):
                    package_name = None

                if package_name == "robot_interface":
                    log_message += (
                        "\n" + attr + ": " + robot_class_to_pretty_string(value)
                    )
                else:
                    log_message += "\n" + str(attr) + ": " + str(value)

            return add_indent(log_message)

        class_name: str = type(self).__name__
        return class_name + robot_class_to_pretty_string(self)


@dataclass
class InspectionStep(Step):
    """
    Base class for all inspection steps which produce results to be uploaded.
    """

    inspections: List[Inspection] = field(default_factory=list, init=False)
    tag_id: Optional[str] = field(default=None, init=False)
    type = "inspection_type"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Inspection

    pass


@dataclass
class MotionStep(Step):
    """
    Base class for all steps which should move the robot, but not return a result.
    """

    pass


@dataclass
class ContinousInspectionStep(Step):
    """
    Base class for all continous inspection steps which produce a result to be uploaded.
    """

    pass


@dataclass
class DriveToPose(MotionStep):
    """
    Step which causes the robot to move to the given pose.
    """

    pose: Pose
    type: Literal["drive_to_pose"] = "drive_to_pose"


@dataclass
class DockingProcedure(MotionStep):
    """
    Step which causes the robot to dock or undock
    """

    behavior: Literal["dock, undock"]
    type: Literal["docking_procedure"] = "docking_procedure"


@dataclass
class TakeImage(InspectionStep):
    """
    Step which causes the robot to take an image towards the given coordinate.
    """

    target: Position
    type: Literal["take_image"] = "take_image"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Image


@dataclass
class TakeThermalImage(InspectionStep):
    """
    Step which causes the robot to take a thermal image towards the given coordinate.
    """

    target: Position
    type: Literal["take_thermal_image"] = "take_thermal_image"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalImage


@dataclass
class TakeVideo(InspectionStep):
    """
    Step which causes the robot to take a video towards the given coordinate.

    Duration of video is given in seconds.
    """

    target: Position
    duration: float
    type: Literal["take_video"] = "take_video"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return Video


@dataclass
class TakeThermalVideo(InspectionStep):
    """
    Step which causes the robot to record thermal video towards the given coordinate

    Duration of video is given in seconds.
    """

    target: Position
    duration: float
    type: Literal["take_thermal_video"] = "take_thermal_video"

    @staticmethod
    def get_inspection_type() -> Type[Inspection]:
        return ThermalVideo


STEPS = Union[
    DriveToPose,
    DockingProcedure,
    TakeImage,
    TakeThermalImage,
    TakeVideo,
    TakeThermalVideo,
]
