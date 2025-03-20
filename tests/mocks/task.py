from alitra import Frame, Orientation, Pose, Position

from robot_interface.models.mission.task import TakeImage


class MockTask:
    @staticmethod
    def take_image() -> TakeImage:
        target_pose = Position(x=1, y=1, z=1, frame=Frame("robot"))
        robot_pose = Pose(
            position=Position(x=0, y=0, z=1, frame=Frame("robot")),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame("robot")),
            frame=Frame("robot"),
        )
        return TakeImage(target=target_pose, robot_pose=robot_pose)
