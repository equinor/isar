import logging
from http import HTTPStatus

from fastapi import Query, Response
from injector import inject
from requests import HTTPError

from isar.apis.models import StartResponse
from isar.config.settings import robot_settings
from isar.mission_planner.mission_planner_interface import (
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.mission_planner.mission_validator import is_robot_capable_of_mission
from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities


class StartMission:
    @inject
    def __init__(
        self,
        mission_planner: MissionPlannerInterface,
        scheduling_utilities: SchedulingUtilities,
    ):
        self.logger = logging.getLogger("api")
        self.mission_planner = mission_planner
        self.scheduling_utilities = scheduling_utilities

    def post(
        self,
        response: Response,
        mission_id: int = Query(
            ...,
            alias="ID",
            title="Mission ID",
            description="ID-number for predefined mission",
        ),
    ):
        self.logger.info("Received request to start new mission")

        ready, response_ready_start = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            start_message, status_code_ready_start = response_ready_start
            response.status_code = status_code_ready_start.value
            return StartResponse(
                message=start_message.message, started=start_message.started
            )

        try:
            mission: Mission = self.mission_planner.get_mission(mission_id)
        except HTTPError as e:
            self.logger.error(e)
            message: str = e.response.content.decode()
            response.status_code = e.response.status_code
            return StartResponse(message=message, started=False)
        except MissionPlannerError as e:
            self.logger.error(e)
            message = e.args[0] if e.args else ""
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return StartResponse(message=message, started=False)

        robot_capable: bool = is_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )
        if not robot_capable:
            response.status_code = HTTPStatus.BAD_REQUEST
            return StartResponse(
                message="Robot don't have necessary capabilities for the given mission",
                started=False,
            )
        self.logger.info(f"Starting mission: {mission.id}")
        response_scheduler = self.scheduling_utilities.start_mission(mission=mission)
        self.logger.info(f"Received response from State Machine: {response_scheduler}")

        message_scheduler, status_code_scheduler = response_scheduler
        response.status_code = status_code_scheduler.value
        return StartResponse(
            message=message_scheduler.message,
            started=message_scheduler.started,
            mission_id=str(mission.id),
        )
