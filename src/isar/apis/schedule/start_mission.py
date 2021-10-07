import logging
from http import HTTPStatus

from flask import request
from flask_restx import Namespace, Resource, fields
from injector import inject

from isar.config import config
from isar.mission_planner.mission_planner_interface import (
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.models.communication.messages import StartMissionMessages
from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities

api = Namespace(
    config.get("api_namespaces", "eqrobot_schedule_namespace"),
    description="Scheduling operations for the robot",
)

start_response = api.model(
    "mission_started", {"mission_started": fields.Boolean, "message": fields.String}
)


@api.route(
    "/start-mission",
    doc={
        "description": "Start a mission",
        "params": {
            "mission_id": {
                "description": "The id of the mission to be started",
                "type": "int",
            }
        },
    },
)
class StartMission(Resource):
    @inject
    def __init__(
        self,
        mission_planner: MissionPlannerInterface,
        scheduling_utilities: SchedulingUtilities,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.mission_planner = mission_planner
        self.scheduling_utilities = scheduling_utilities

    @api.response(HTTPStatus.OK, "Success", start_response)
    @api.response(HTTPStatus.REQUEST_TIMEOUT, "Request Timeout", start_response)
    @api.response(HTTPStatus.CONFLICT, "Conflict", start_response)
    @api.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @api.response(HTTPStatus.NOT_FOUND, "Not Found")
    def get(self):
        try:
            mission_id = int(request.args.get("mission_id"))
        except Exception as e:
            message = StartMissionMessages.bad_request()
            self.logger.error(f"{message} {e}")
            return message, HTTPStatus.BAD_REQUEST

        try:
            mission: Mission = self.mission_planner.get_mission(mission_id=mission_id)
        except MissionPlannerError as e:
            self.logger.error(f"Failed to read mission\n {e}")
            message = StartMissionMessages.mission_not_found()
            return message, HTTPStatus.NOT_FOUND

        response = self.scheduling_utilities.start_mission(mission=mission)

        self.logger.info(response)
        return response
