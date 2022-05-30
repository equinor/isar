import logging
from copy import deepcopy
from typing import Any, Optional

from alitra import Pose
from injector import inject

from isar.config.settings import settings
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues import QueueIO, Queues, QueueTimeoutError
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

    def get_state(self) -> States:
        return self.queues.state.check()

    def start_mission(self, mission: Mission, initial_pose: Optional[Pose]) -> None:
        self._send_command(
            StartMissionMessage(mission=deepcopy(mission), initial_pose=initial_pose),
            self.queues.start_mission,
        )

    def pause_mission(self) -> None:
        self._send_command(True, self.queues.pause_mission)

    def resume_mission(self) -> None:
        self._send_command(True, self.queues.resume_mission)

    def stop_mission(self) -> None:
        self._send_command(True, self.queues.stop_mission)

    def _send_command(self, input: Any, queueio: QueueIO) -> Any:
        queueio.input.put(input)
        try:
            return QueueUtilities.check_queue(
                queueio.output,
                self.queue_timeout,
            )
        except QueueTimeoutError as e:
            QueueUtilities.clear_queue(queueio.input)
            self.logger.error("Timeout while communicating with state machine")
            raise e
