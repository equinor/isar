from alitra import Frame, Position

from robot_interface.models.mission.task import ReturnToHome, TakeImage
from tests.mocks.pose import MockPose


class MockTask:
    @staticmethod
    def return_home() -> ReturnToHome:
        return ReturnToHome(pose=MockPose.default_pose())

    @staticmethod
    def take_image() -> TakeImage:
        target_pose = Position(x=1, y=1, z=1, frame=Frame("robot"))
        robot_pose = Position(x=0, y=0, z=1, frame=Frame("robot"))
        return TakeImage(target=target_pose, robot_pose=robot_pose)
