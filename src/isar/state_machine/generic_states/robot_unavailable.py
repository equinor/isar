import logging
import time
from enum import Enum
from typing import TYPE_CHECKING

from isar.models.communication.queues.queue_utils import check_shared_state
from robot_interface.models.mission.status import RobotStatus


class RobotUnavailableStates(str, Enum):
    BlockedProtectiveStop = "blockedProtectiveStop"
    Offline = "offline"


if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class RobotUnavailable:
    def __init__(
        self,
        state_machine: "StateMachine",
        state: RobotUnavailableStates,
    ) -> None:
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.shared_state = self.state_machine.shared_state
        self.signal_state_machine_to_stop = state_machine.signal_state_machine_to_stop
        self.state: RobotUnavailableStates = state

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        return

    def _run(self) -> None:
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.state.name
                )
                break

            robot_status: RobotStatus = check_shared_state(
                self.shared_state.robot_status
            )

            expected_status = (
                RobotStatus.BlockedProtectiveStop
                if self.state == RobotUnavailableStates.BlockedProtectiveStop
                else RobotStatus.Offline
            )
            if robot_status != expected_status:
                transition = self.state_machine.robot_status_changed  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
