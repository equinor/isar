from dataclasses import dataclass

from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.position import Position


@dataclass
class Pose:
    position: Position
    orientation: Orientation
    frame: Frame
