import logging
from http import HTTPStatus

from flask import request
from flask_restx import Namespace, Resource, fields
from injector import inject

from isar.config import config
from isar.models.communication.messages import StartMessage, StartMissionMessages
from isar.models.mission import Mission
from isar.services.service_connections.echo.echo_service import EchoServiceInterface
from isar.services.utilities.scheduling_utilities import SchedulingUtilities

api = Namespace(
    config.get("api_namespaces", "eqrobot_schedule_namespace"),
    description="Scheduling operations for the robot",
)

start_response = api.model(
    "mission_started", {"mission_started": fields.Boolean, "message": fields.String}
)


@api.route(
    "/start-echo-mission",
    doc={
        "description": "Start the mission created in the Echo Mission Planner tool.",
        "params": {
            "mission_id": {
                "description": "The ID given to the mission in Echo.",
                "type": "int",
            }
        },
    },
)
class StartEchoMission(Resource):
    @inject
    def __init__(
        self,
        echo_service: EchoServiceInterface,
        scheduling_utilities: SchedulingUtilities,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.echo_service = echo_service
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
            message: StartMessage = StartMissionMessages.bad_request()
            self.logger.error(f"{message} {e}")
            return message, HTTPStatus.BAD_REQUEST

        mission: Mission = self.echo_service.get_mission(mission_id=mission_id)

        if mission is None:
            message: StartMessage = StartMissionMessages.mission_not_found()
            return message, HTTPStatus.NOT_FOUND

        ready, response = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            return response

        response = self.scheduling_utilities.start_mission(mission=mission)

        self.logger.info(response)
        return response
