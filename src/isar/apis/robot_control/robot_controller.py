import logging

from dependency_injector.wiring import inject
from fastapi import HTTPException

from isar.apis.models.models import RobotInfoResponse
from isar.config.settings import robot_settings, settings
from isar.services.utilities.robot_utilities import RobotUtilities
from robot_interface.models.robots.media import MediaConfig


class RobotController:
    @inject
    def __init__(
        self,
        robot_utilities: RobotUtilities,
    ):
        self.robot_utilities: RobotUtilities = robot_utilities
        self.logger = logging.getLogger("api")

    def generate_media_config(self) -> MediaConfig:
        media_config: MediaConfig = self.robot_utilities.generate_media_config()
        if media_config is None:
            raise HTTPException(
                status_code=204,
                detail="Robot has no media config",
            )
        return media_config

    def get_info(self) -> RobotInfoResponse:
        return RobotInfoResponse(
            robot_package=settings.ROBOT_PACKAGE,
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            robot_capabilities=robot_settings.CAPABILITIES,
            robot_map_name=settings.DEFAULT_MAP,
            plant_short_name=settings.PLANT_SHORT_NAME,
        )
