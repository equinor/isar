from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.position import Position
from robot_interface.models.mission import DriveToPose, TakeImage
from tests.mocks.pose import MockPose


class MockTask:
    drive_to = DriveToPose(pose=MockPose.default_pose)
    take_image_in_coordinate_direction = TakeImage(
        target=Position(x=1, y=1, z=1, frame=Frame.Robot)
    )
