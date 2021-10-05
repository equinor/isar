import logging
from http import HTTPStatus

from flask_restx import Namespace, Resource, fields
from injector import inject
from isar.config import config
from isar.services.utilities.queue_utilities import QueueUtilities

from isar.models.communication.messages import StartMessage, StartMissionMessages
from isar.models.communication.queues.queues import Queues
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError

api = Namespace(config.get("api_namespaces", "eqrobot_telemetry_namespace"))

status_response = api.model(
    "status",
    {
        "mission_status": fields.String(example="scheduled"),
        "mission_in_progress": fields.Boolean,
        "current_mission_instance_id": fields.Integer(example=1354),
        "current_mission_step": fields.String(example="Dictionary"),
        "mission_schedule": fields.String(example="List"),
        "current_state": fields.String(example="idle"),
    },
)

status_timeout_response = api.model(
    "status_request_timeout",
    {
        "status": fields.String(example="null"),
        "message": fields.String(
            example="Waiting for return message on queue timed out"
        ),
    },
)


@api.route(
    "/mission-status",
    doc={"description": "Retrieve the status of the current mission."},
)
class MissionStatus(Resource):
    @inject
    def __init__(self, queues: Queues, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.queues = queues
        self.queue_timeout: int = config.getint("mission", "eqrobot_queue_timeout")

    @api.response(HTTPStatus.OK, "Success", status_response)
    @api.response(
        HTTPStatus.REQUEST_TIMEOUT, "Request Timeout", status_timeout_response
    )
    def get(self):
        self.queues.mission_status.input.put(True)
        try:
            message: StartMessage = QueueUtilities.check_queue(
                self.queues.mission_status.output, self.queue_timeout
            )
        except QueueTimeoutError:
            response = StartMissionMessages.queue_timeout(), HTTPStatus.REQUEST_TIMEOUT
            self.logger.error(response)
            return response

        response = message, HTTPStatus.OK
        self.logger.info(response)
        return response
