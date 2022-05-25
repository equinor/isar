import logging
from http import HTTPStatus

from fastapi import Query, Response
from injector import inject
from requests import HTTPError

from isar.apis.models import StartMissionResponse
from isar.config.settings import robot_settings, settings
from isar.mission_planner.mission_planner_interface import (
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.mission_planner.mission_validator import is_robot_capable_of_mission
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States


class StartMission:
    @inject
    def __init__(
        self,
        mission_planner: MissionPlannerInterface,
        scheduling_utilities: SchedulingUtilities,
        queue_timeout: int = settings.QUEUE_TIMEOUT,
    ):
        self.logger = logging.getLogger("api")
        self.mission_planner: MissionPlannerInterface = mission_planner
        self.scheduling_utilities: SchedulingUtilities = scheduling_utilities
        self.queue_timeout: int = queue_timeout

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

        state: States = self.scheduling_utilities.get_state()
        if not state or state != States.Idle:
            response.status_code = HTTPStatus.CONFLICT.value
            return

        try:
            mission: Mission = self.mission_planner.get_mission(mission_id)
        except HTTPError as e:
            self.logger.error(e)
            response.status_code = e.response.status_code
            return
        except MissionPlannerError as e:
            self.logger.error(e)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        robot_capable: bool = is_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )
        if not robot_capable:
            self.logger.error("Robot is not capable of performing mission")
            response.status_code = HTTPStatus.BAD_REQUEST.value
            return

        self.logger.info(f"Starting mission: {mission.id}")

        try:
            self.scheduling_utilities.start_mission(mission=mission)
        except QueueTimeoutError:
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return
        return StartMissionResponse(**mission.api_response_dict())
