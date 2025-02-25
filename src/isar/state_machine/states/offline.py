import logging
import time
from typing import TYPE_CHECKING

from transitions import State

from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Offline(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="offline", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        return

    def _run(self) -> None:
        while True:
            robot_status = self.state_machine.get_robot_status()
            if robot_status == RobotStatus.BlockedProtectiveStop:
                transition = self.state_machine.robot_protective_stop_engaged  # type: ignore
                break
            elif robot_status != RobotStatus.Offline:
                transition = self.state_machine.robot_turned_online  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
