from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.joints import Joints
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position


def mock_joints(
    j1: float = 1, j2: float = 1, validate_constraints: bool = True
) -> Joints:
    return Joints(j1=j1, j2=j2, validate_constraints=validate_constraints)


def mock_pose(
    position: Position = Position(x=1, y=1, z=1, frame=Frame.Robot),
    orientation: Orientation = Orientation(
        x=0, y=0, z=0.7071068, w=0.7071068, frame=Frame.Robot
    ),
) -> Pose:
    return Pose(position=position, orientation=orientation, frame=Frame.Robot)
