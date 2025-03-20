import logging
import time
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.models.communication.queues.queue_utils import check_shared_state
from isar.services.utilities.threaded_request import ThreadedRequest
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class BlockedProtectiveStop(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(
            name="blocked_protective_stop", on_enter=self.start, on_exit=self.stop
        )
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.robot_status_thread: Optional[ThreadedRequest] = None
        self.shared_state = self.state_machine.shared_state
        self.signal_state_machine_to_stop = state_machine.signal_state_machine_to_stop

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        return

    def _run(self) -> None:
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.__class__.__name__
                )
                break

            robot_status: RobotStatus = check_shared_state(
                self.shared_state.robot_status
            )
            if robot_status != RobotStatus.BlockedProtectiveStop:
                transition = self.state_machine.robot_status_changed  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
