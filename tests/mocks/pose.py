from alitra import Frame, Orientation, Pose, Position


class MockPose:
    @staticmethod
    def default_pose():
        return Pose(
            position=Position(x=0, y=0, z=0, frame=Frame("robot")),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame("robot")),
            frame=Frame("robot"),
        )
