import logging
import time
from typing import TYPE_CHECKING, Optional

from transitions import State

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

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        if self.robot_status_thread:
            self.robot_status_thread.wait_for_thread()
        self.robot_status_thread = None

    def _run(self) -> None:
        while True:
            if not self.robot_status_thread:
                self.robot_status_thread = ThreadedRequest(
                    request_func=self.state_machine.robot.robot_status
                )
                self.robot_status_thread.start_thread(
                    name="State Machine BlockedProtectiveStop Get Robot Status"
                )

            robot_status = self.state_machine.get_robot_status()

            if robot_status == RobotStatus.Offline:
                transition = self.state_machine.robot_turned_offline  # type: ignore
                break
            elif robot_status != RobotStatus.BlockedProtectiveStop:
                transition = self.state_machine.robot_protective_stop_disengaged  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
