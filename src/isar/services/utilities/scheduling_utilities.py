import logging
from copy import deepcopy
from http import HTTPStatus
from typing import Optional, Tuple

from injector import inject

from isar.config import config
from isar.models.communication.messages import StartMessage, StartMissionMessages
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.models.communication.status import Status
from isar.models.mission import Mission
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.state_machine.states_enum import States


class SchedulingUtilities:
    """
    Contains utility functions for scheduling missions from the API. The class handles required thread communication
    through queues to the state machine.
    """

    @inject
    def __init__(
        self,
        queues: Queues,
        queue_timeout: int = config.getint("DEFAULT", "queue_timeout"),
    ):
        self.queues = queues
        self.queue_timeout: int = queue_timeout
        self.logger = logging.getLogger("api")

    def ready_to_start_mission(self) -> Tuple[bool, Optional[Tuple[StartMessage, int]]]:
        """
        Checks the current mission status by communicating with the state machine thread through queues.
        :return: (True, None) if the mission may be started. Otherwise (False, response) with a relevant response
        message indicating the cause.
        """
        self.queues.mission_status.input.put(True)
        try:
            status: Status = QueueUtilities.check_queue(
                self.queues.mission_status.output, self.queue_timeout
            )
        except QueueTimeoutError:
            error_message = (
                StartMissionMessages.queue_timeout(),
                HTTPStatus.REQUEST_TIMEOUT,
            )
            self.logger.error(error_message)
            return False, error_message

        if status.mission_in_progress or status.current_state != States.Idle:
            message = StartMissionMessages.mission_in_progress()
            error_message = message, HTTPStatus.CONFLICT
            return False, error_message
        return True, None

    def start_mission(self, mission: Mission) -> Tuple[StartMessage, int]:
        """
        Starts a mission by communicating with the state machine thread through queues.
        :param mission: A Mission containing the mission tasks to be started.
        :return: (message, status_code) is returned indicating the success and cause of the operation.
        """
        self.queues.start_mission.input.put(deepcopy(mission))
        try:
            start_message: StartMessage = QueueUtilities.check_queue(
                self.queues.start_mission.output, self.queue_timeout
            )
        except QueueTimeoutError:
            error_message = (
                StartMissionMessages.queue_timeout(),
                HTTPStatus.REQUEST_TIMEOUT,
            )
            self.logger.error(error_message)
            return error_message
        if not start_message.started:
            error_message = start_message, HTTPStatus.CONFLICT
            self.logger.error(error_message)
            return error_message

        error_message = start_message, HTTPStatus.OK
        self.logger.info(error_message)
        return error_message
