import logging
from logging import Logger

from models.geometry.frame import Frame
from models.geometry.orientation import Orientation
from models.geometry.pose import Pose
from models.geometry.position import Position
from robot_interfaces.robot_telemetry_interface import RobotTelemetryInterface


class MockTelemetry(RobotTelemetryInterface):
    def __init__(
        self,
        pose: Pose = Pose(
            position=Position(x=0, y=0, z=0, frame=Frame.Robot),
            orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame.Robot),
            frame=Frame.Robot,
        ),
    ):
        self.logger: Logger = logging.getLogger()
        self.robot_pose_return_value: Pose = pose

    def robot_pose(self) -> Pose:
        self.logger.info("Mock for robot_pose in Telemetry was called")
        return self.robot_pose_return_value
