import logging
import time
from typing import TYPE_CHECKING, Callable

from transitions import State

from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class UnknownStatus(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="unknown_status", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        return

    def _run(self) -> None:
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop  # type: ignore
                break

            robot_status = self.state_machine.get_robot_status()
            if robot_status == RobotStatus.Docked:
                transition = self.state_machine.robot_docked  # type: ignore
                break
            elif robot_status == RobotStatus.Offline:
                transition = self.state_machine.robot_turned_offline  # type: ignore
                break
            elif robot_status == RobotStatus.BlockedProtectiveStop:
                transition = self.state_machine.robot_protective_stop_engaged  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)
        transition()
