import logging

from injector import inject

from isar.config.settings import settings

from isar.config.settings import settings

from robot_interface.robot_interface import RobotInterface


class RobotUtilities:
    """
    Contains utility functions for scheduling missions from the API. The class handles
    required thread communication through queues to the state machine.
    """

    @inject
    def __init__(
        self,
        robot: RobotInterface,
    ):
        self.robot: RobotInterface = robot
        self.logger = logging.getLogger("api")

    def generate_robot_media_config(self) -> str:
        return self.robot.generate_media_config(settings.ISAR_ID, settings.ROBOT_NAME)
