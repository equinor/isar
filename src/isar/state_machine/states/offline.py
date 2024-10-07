import logging
import time
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.config.settings import settings
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions.robot_exceptions import RobotException
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Offline(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="offline", on_enter=self.start, on_exit=self.stop)
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
                    name="State Machine Offline Get Robot Status"
                )

            try:
                robot_status: RobotStatus = self.robot_status_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue

            except (RobotException,) as e:
                self.logger.error(
                    f"Failed to get robot status because: {e.error_description}"
                )

            if robot_status != RobotStatus.Offline:
                transition = self.state_machine.robot_turned_online  # type: ignore
                break

            self.robot_status_thread = None
            time.sleep(settings.ROBOT_API_STATUS_POLL_INTERVAL)

        transition()
