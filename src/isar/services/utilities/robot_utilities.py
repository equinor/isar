from robot_interface.models.robots.media import MediaConfig
from robot_interface.robot_interface import RobotInterface


class RobotUtilities:
    """
    Contains utility functions for getting robot information from the API.
    """

    def __init__(
        self,
        robot: RobotInterface,
    ):
        self.robot: RobotInterface = robot

    def generate_media_config(self) -> MediaConfig | None:
        return self.robot.generate_media_config()
