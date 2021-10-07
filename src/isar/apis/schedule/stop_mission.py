import logging
from http import HTTPStatus

from flask_restx import Namespace, Resource, fields
from injector import inject

from isar.config import config
from isar.services.utilities.scheduling_utilities import SchedulingUtilities

api = Namespace(
    config.get("api_namespaces", "eqrobot_schedule_namespace"),
    description="Scheduling operations for the robot",
)

stop_response = api.model(
    "mission_stopped", {"mission_stopped": fields.Boolean, "message": fields.String}
)


@api.route(
    "/stop_mission",
    doc={
        "description": "NB: This does not necessarily stop the actual mission on the  "
        "robot, only if the robot has stop functionality  "
        "This will only stop the mission in the State Machine itself."
    },
)
class StopMission(Resource):
    @inject
    def __init__(self, scheduling_utilities: SchedulingUtilities, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.scheduling_utilities = scheduling_utilities

    @api.response(HTTPStatus.OK, "Success", stop_response)
    @api.response(HTTPStatus.REQUEST_TIMEOUT, "Request Timeout", stop_response)
    def get(self):

        response = self.scheduling_utilities.stop_mission()
        self.logger.info(response)
        return response
