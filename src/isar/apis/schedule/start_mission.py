import logging
from dataclasses import asdict
from http import HTTPStatus

from fastapi import Query
from fastapi.responses import JSONResponse
from injector import inject

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
            return JSONResponse(
                content=asdict(message), status_code=HTTPStatus.NOT_FOUND
            )

        ready, response = self.scheduling_utilities.ready_to_start_mission()
        if ready:
            response = self.scheduling_utilities.start_mission(mission=mission)
            self.logger.info(response)

        message, status_code = response
        return JSONResponse(content=asdict(message), status_code=status_code)
