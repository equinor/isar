import logging
from http import HTTPStatus
from typing import Optional

from fastapi import Response
from injector import inject

from isar.config.settings import settings
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States


class PauseMission:
    @inject
    def __init__(
        self,
        queues: Queues,
        scheduling_utilities: SchedulingUtilities,
        queue_timeout: int = settings.QUEUE_TIMEOUT,
    ):
        self.logger = logging.getLogger("api")
        self.queues: Queues = queues
        self.queue_timeout: int = queue_timeout
        self.scheduling_utilities: SchedulingUtilities = scheduling_utilities

    def pause(self, response: Response):
        self.logger.info("Received request to pause current mission")

        state: Optional[States] = self.scheduling_utilities.get_state()

        if not state or state not in [States.InitiateStep, States.Monitor]:
            self.logger.info("Bad request - Pause command received in invalid state")
            response.status_code = HTTPStatus.BAD_REQUEST.value
            return

        self.queues.pause_mission.input.put(True)
        try:
            QueueUtilities.check_queue(
                self.queues.pause_mission.output,
                self.queue_timeout,
            )
        except QueueTimeoutError:
            QueueUtilities.clear_queue(self.queues.pause_mission.input)
            self.logger.error("Timeout while waiting on response for pause command")
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value

    def resume(self, response: Response):
        self.logger.info("Received request to resume current mission")

        state: Optional[States] = self.scheduling_utilities.get_state()
        if not state or state != States.Paused:
            self.logger.info("Bad request - Resume command received in invalid state")
            response.status_code = HTTPStatus.BAD_REQUEST.value
            return

        self.queues.resume_mission.input.put(True)
        try:
            QueueUtilities.check_queue(
                self.queues.resume_mission.output,
                self.queue_timeout,
            )
        except QueueTimeoutError:
            QueueUtilities.clear_queue(self.queues.resume_mission.input)
            self.logger.error("Timeout while waiting on response for pause command")
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
