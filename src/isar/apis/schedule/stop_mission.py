import logging
from http import HTTPStatus

from flask_restx import Namespace, Resource, fields
from injector import inject

from isar.config import config
from isar.models.communication.messages import StopMessage, StopMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.queue_utilities import QueueUtilities

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
    def __init__(self, queues: Queues, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.queues = queues
        self.queue_timeout: int = config.getint("mission", "eqrobot_queue_timeout")

    @api.response(HTTPStatus.OK, "Success", stop_response)
    @api.response(HTTPStatus.REQUEST_TIMEOUT, "Request Timeout", stop_response)
    def get(self):

        self.queues.stop_mission.input.put(True)

        try:
            message: StopMessage = QueueUtilities.check_queue(
                self.queues.stop_mission.output,
                self.queue_timeout,
            )
        except QueueTimeoutError:
            response = StopMissionMessages.queue_timeout(), HTTPStatus.REQUEST_TIMEOUT
            self.logger.error(response)
            return response
        response = message, HTTPStatus.OK
        self.logger.info(response)
        return response
