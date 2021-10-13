from alitra import Quaternion

from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation


def orientation_from_quaternion(quaternion: Quaternion) -> Orientation:
    frame: Frame
    if quaternion.frame == Frame.Robot.value:
        frame = Frame.Robot
    elif quaternion.frame == Frame.Asset.value:
        frame = Frame.Asset
    else:
        raise ValueError(f"Frame: {quaternion.frame} is not supported.")

    return Orientation(
        x=quaternion.x, y=quaternion.y, z=quaternion.z, w=quaternion.w, frame=frame
    )


def quaternion_from_orientation(orientation: Orientation) -> Quaternion:
    return Quaternion(
        x=orientation.x,
        y=orientation.y,
        z=orientation.z,
        w=orientation.w,
        frame=orientation.frame.value,
    )
