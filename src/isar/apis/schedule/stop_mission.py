import logging
from http import HTTPStatus

from fastapi import Response
from injector import inject

from isar.apis.models import StopResponse
from isar.config.settings import settings
from isar.models.communication.messages import StopMessage, StopMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.queue_utilities import QueueUtilities


class StopMission:
    @inject
    def __init__(self, queues: Queues):
        self.logger = logging.getLogger("api")
        self.queues = queues
        self.queue_timeout: int = settings.QUEUE_TIMEOUT

    def post(self, response: Response):
        self.logger.info("Received request to stop current mission")
        self.queues.stop_mission.input.put(True)

        try:
            message: StopMessage = QueueUtilities.check_queue(
                self.queues.stop_mission.output,
                self.queue_timeout,
            )
        except QueueTimeoutError:
            message = StopMissionMessages.queue_timeout()
            self.logger.error((message, HTTPStatus.REQUEST_TIMEOUT))
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return StopResponse(message=message.message, stopped=message.stopped)
        self.logger.info(response)
        return StopResponse(message=message.message, stopped=message.stopped)
