import logging
from dataclasses import asdict
from http import HTTPStatus

from injector import inject
from starlette.responses import JSONResponse

from isar.config import config
from isar.models.communication.messages import StopMessage, StopMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.queue_utilities import QueueUtilities


class StopMission:
    @inject
    def __init__(self, queues: Queues):
        self.logger = logging.getLogger("api")
        self.queues = queues
        self.queue_timeout: int = config.getint("DEFAULT", "queue_timeout")

    def post(self):

        self.queues.stop_mission.input.put(True)

        try:
            message: StopMessage = QueueUtilities.check_queue(
                self.queues.stop_mission.output,
                self.queue_timeout,
            )
        except QueueTimeoutError:
            message = StopMissionMessages.queue_timeout()
            status_code = HTTPStatus.REQUEST_TIMEOUT
            self.logger.error((message, status_code))
            return JSONResponse(content=asdict(message), status_code=status_code)
        response = message, HTTPStatus.OK
        self.logger.info(response)
        return JSONResponse(content=asdict(message), status_code=HTTPStatus.OK)
