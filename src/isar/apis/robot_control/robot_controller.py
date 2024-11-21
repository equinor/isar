import logging
from typing import List

from injector import inject

from isar.apis.models.models import (
    RobotInfoResponse,
    TaskResponse,
)
from isar.config.settings import robot_settings, settings
from isar.services.utilities.robot_utilities import RobotUtilities
from robot_interface.models.mission.task import Task


class RobotController:
    @inject
    def __init__(
        self,
        robot_utilities: RobotUtilities,
    ):
        self.robot_utilities: RobotUtilities = robot_utilities
        self.logger = logging.getLogger("api")

    def generate_media_stream_config(self):
        return self.robot_utilities.generate_robot_media_config()

    def get_info(self):
        return RobotInfoResponse(
            robot_package=settings.ROBOT_PACKAGE,
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            robot_map_name=settings.DEFAULT_MAP,
            robot_capabilities=robot_settings.CAPABILITIES,
        )

    def _task_api_response(self, task: Task) -> TaskResponse:
        steps: List[dict] = []
        for step in task.steps:
            steps.append({"id": step.id, "type": step.__class__.__name__})

        return TaskResponse(id=task.id, tag_id=task.tag_id, steps=steps)
