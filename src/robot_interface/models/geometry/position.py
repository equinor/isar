from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from robot_interface.models.geometry.frame import Frame


@dataclass
class Position:
    x: float
    y: float
    z: float
    frame: Frame

    def __eq__(self, other):
        if not isinstance(other, Position):
            return False
        if (
            np.allclose(a=[self.x, self.y, self.z], b=[other.x, other.y, other.z])
            and self.frame == other.frame
        ):
            return True
        return False

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

    @staticmethod
    def from_list(input_list: List, frame: Frame) -> Position:
        return Position(x=input_list[0], y=input_list[1], z=input_list[2], frame=frame)
