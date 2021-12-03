from dataclasses import dataclass
from typing import List

import numpy as np
from alitra import Quaternion
from alitra.convert import quaternion_to_euler

from robot_interface.models.geometry.frame import Frame


@dataclass
class Orientation:
    """
    This class represents an orientation using quaternions. The quaternion is used throughout the project.
    Methods that utilize Euler angles will all follow the yaw, pitch, roll convention which rotates around the ZYX axis
    with intrinsic rotations.
    """

    x: float
    y: float
    z: float
    w: float
    frame: Frame

    def __eq__(self, other):
        if not isinstance(other, Orientation):
            return False
        if (
            np.allclose(
                a=[self.x, self.y, self.z, self.w],
                b=[other.x, other.y, other.z, other.w],
                atol=1e-10,
            )
            and self.frame == other.frame
        ):
            return True
        return False

    def as_euler(
        self,
        degrees: bool = False,
        wrap_angles: bool = False,
    ) -> list:
        """
        Retrieve the orientation as yaw, pitch, roll Euler coordinates. This function uses the ZYX intrinsic rotations
        as standard convention.
        :param degrees: Set to true to retrieve angles as degrees.
        :return: List of euler angles [yaw, pitch, roll]
        """

        euler: list = (
            quaternion_to_euler(
                Quaternion(
                    x=self.x, y=self.y, z=self.z, w=self.w, frame=self.frame.value
                ),
                sequence="ZYX",
                degrees=degrees,
            )
            .as_np_array()
            .tolist()
        )

        if wrap_angles:
            base = 360.0 if degrees else 2 * np.pi
            euler = list(map(lambda angle: ((angle + base) % (base)), euler))

        return euler

    def yaw(self, degrees: bool = False, wrap_angles: bool = False) -> float:
        euler_angles: list = self.as_euler(degrees=degrees, wrap_angles=wrap_angles)
        return euler_angles[0]

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z, self.w]
