from dataclasses import dataclass

from models.geometry.frame import Frame
from models.geometry.orientation import Orientation
from models.geometry.position import Position


@dataclass
class Pose:
    position: Position
    orientation: Orientation
    frame: Frame
