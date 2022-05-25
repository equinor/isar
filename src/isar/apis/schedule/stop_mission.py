import logging
from http import HTTPStatus

from fastapi import Response
from injector import inject

from isar.config.settings import settings
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.queue_utilities import QueueUtilities


class StopMission:
    @inject
    def __init__(self, queues: Queues, queue_timeout: int = settings.QUEUE_TIMEOUT):
        self.logger = logging.getLogger("api")
        self.queues: Queues = queues
        self.queue_timeout: int = queue_timeout

    def post(self, response: Response):
        self.logger.info("Received request to stop current mission")
        self.queues.stop_mission.input.put(True)

        try:
            QueueUtilities.check_queue(
                self.queues.stop_mission.output,
                self.queue_timeout,
            )
            self.logger.info("Mission successfully stopped")
            return
        except QueueTimeoutError:
            QueueUtilities.clear_queue(self.queues.stop_mission.input)
            self.logger.error("Timeout while communicating with state machine")
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return
