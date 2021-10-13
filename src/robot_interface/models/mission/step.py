from dataclasses import dataclass
from typing import Literal, Optional, Union

from robot_interface.models.geometry.joints import Joints
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position


@dataclass
class Step:
    """
    Base class for all Steps in a mission.
    """


@dataclass
class InspectionStep(Step):
    """
    Base class for all inspection steps which produce a result to be uploaded.
    """

    pass


@dataclass
class MotionStep(Step):
    """
    Base class for all steps which should cause the robot to move, but not return a result.
    """

    pass


@dataclass
class DriveToPose(MotionStep):
    """
    Step which causes the robot to move to the given pose.
    """

    pose: Pose
    step_name: Literal["drive_to_pose"] = "drive_to_pose"


@dataclass
class DockingProcedure(MotionStep):
    """
    Step which causes the robot to dock or undock
    """

    behavior: Literal["dock, undock"]
    step_name: Literal["docking_procedure"] = "docking_procedure"


@dataclass
class TakeImage(InspectionStep):
    """
    Step which causes the robot to take an image towards the given coordinate.
    """

    target: Position
    step_name: Literal["take_image"] = "take_image"
    computed_joints: Optional[Joints] = None
    tag_id: Optional[str] = None


@dataclass
class TakeThermalImage(InspectionStep):
    """
    Step which causes the robot to take a thermal image towards the given coordinate.
    """

    target: Position
    step_name: Literal["take_thermal_image"] = "take_thermal_image"
    tag_id: Optional[str] = None


STEPS = Union[DriveToPose, DockingProcedure, TakeImage, TakeThermalImage]
