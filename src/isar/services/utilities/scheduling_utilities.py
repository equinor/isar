import logging
from copy import deepcopy
from typing import Optional

from injector import inject

from isar.config.settings import settings
from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.communication.queues.queues import Queues
from isar.models.mission.mission import Mission
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.state_machine.states_enum import States


class SchedulingUtilities:
    """
    Contains utility functions for scheduling missions from the API. The class handles
    required thread communication through queues to the state machine.
    """

    @inject
    def __init__(self, queues: Queues, queue_timeout: int = settings.QUEUE_TIMEOUT):
        self.queues = queues
        self.queue_timeout: int = queue_timeout
        self.logger = logging.getLogger("api")

    def get_state(self) -> Optional[States]:
        self.queues.mission_status.input.put(True)
        try:
            return QueueUtilities.check_queue(
                self.queues.mission_status.output, self.queue_timeout
            )
        except QueueTimeoutError:
            self.logger.error(
                "Timeout while trying to get the state of the state machine"
            )
            QueueUtilities.clear_queue(self.queues.mission_status.input)
            return None

    def start_mission(self, mission: Mission) -> None:
        self.queues.start_mission.input.put(deepcopy(mission))
        try:
            QueueUtilities.check_queue(
                self.queues.start_mission.output, self.queue_timeout
            )
        except QueueTimeoutError as e:
            QueueUtilities.clear_queue(self.queues.start_mission.input)
            self.logger.error(
                "Timeout while trying to start mission with state machine"
            )
            raise e
