from alitra import Frame, Position

from robot_interface.models.mission.step import DriveToPose, TakeImage
from tests.mocks.pose import MockPose


class MockStep:
    @staticmethod
    def drive_to() -> DriveToPose:
        return DriveToPose(pose=MockPose.default_pose())

    @staticmethod
    def take_image_in_coordinate_direction() -> TakeImage:
        return TakeImage(target=Position(x=1, y=1, z=1, frame=Frame("robot")))
