import logging
from http import HTTPStatus

from fastapi import Query, Response
from injector import inject

from isar.apis.models import StartResponse
from isar.mission_planner.mission_planner_interface import (
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.models.communication.messages.start_message import StartMissionMessages
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

        try:
            mission: Mission = self.mission_planner.get_mission(mission_id)
        except MissionPlannerError as e:
            message = StartMissionMessages.mission_not_found()
            self.logger.error(e)
            response.status_code = HTTPStatus.NOT_FOUND.value
            return StartResponse(message=message.message, started=message.started)

        ready, response_ready_start = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            message, status_code_ready_start = response_ready_start
            response.status_code = status_code_ready_start.value
            return StartResponse(message=message.message, started=message.started)

        response_scheduler = self.scheduling_utilities.start_mission(mission=mission)
        self.logger.info(response_scheduler)

        message_scheduler, status_code_scheduler = response_scheduler
        response.status_code = status_code_scheduler.value
        return StartResponse(
            message=message_scheduler.message,
            started=message_scheduler.started,
            mission_id=str(mission.id),
        )
