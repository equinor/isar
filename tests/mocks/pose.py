from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position


class MockPose:
    default_pose = Pose(
        position=Position(x=0, y=0, z=0, frame=Frame.Robot),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame.Robot),
        frame=Frame.Robot,
    )
