from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position


def mock_pose(
    position: Position = Position(x=1, y=1, z=1, frame=Frame.Robot),
    orientation: Orientation = Orientation(
        x=0, y=0, z=0.7071068, w=0.7071068, frame=Frame.Robot
    ),
) -> Pose:
    return Pose(position=position, orientation=orientation, frame=Frame.Robot)
