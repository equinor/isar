import logging

from dependency_injector.wiring import inject

from robot_interface.models.robots.media import MediaConfig
from robot_interface.robot_interface import RobotInterface


class RobotUtilities:
    """
    Contains utility functions for getting robot information from the API.
    """

    @inject
    def __init__(
        self,
        robot: RobotInterface,
    ):
        self.robot: RobotInterface = robot
        self.logger = logging.getLogger("api")

    def generate_media_config(self) -> MediaConfig:
        return self.robot.generate_media_config()
