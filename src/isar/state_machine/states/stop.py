import logging
import time
from typing import TYPE_CHECKING, Callable, Optional

from transitions import State

from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotActionException,
    RobotException,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stop(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="stop", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.stop_thread: Optional[ThreadedRequest] = None
        self._count_number_retries: int = 0

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        if self.stop_thread:
            self.stop_thread.wait_for_thread()
        self.stop_thread = None
        self._count_number_retries = 0

    def _run(self) -> None:
        transition: Callable
        while True:
            if not self.stop_thread:
                self.stop_thread = ThreadedRequest(self.state_machine.robot.stop)
                self.stop_thread.start_thread(name="State Machine Stop Robot")

            if self.state_machine.should_stop_mission():
                self.state_machine.stopped = True

            try:
                self.stop_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue

            except (RobotActionException, RobotException) as e:
                if self.handle_stop_fail(
                    retry_limit=self.state_machine.stop_robot_attempts_limit,
                    error_message=ErrorMessage(
                        error_reason=e.error_reason,
                        error_description=e.error_description,
                    ),
                ):
                    transition = self.state_machine.mission_stopped  # type: ignore
                    break

                self.logger.warning(
                    f"\nFailed to stop robot because: {e.error_description}"
                    f"\nAttempting to stop the robot again"
                )

                self.stop_thread = None
                continue
            if self.state_machine.stopped:
                transition = self.state_machine.mission_stopped  # type: ignore
            else:
                transition = self.state_machine.mission_paused  # type: ignore
            break

        transition()

    def handle_stop_fail(self, retry_limit: int, error_message: ErrorMessage) -> bool:
        self._count_number_retries += 1
        if self._count_number_retries > retry_limit:
            self.state_machine.current_task.error_message = error_message

            self.logger.error(
                f"\nFailed to stop the robot after {retry_limit} attempts because: "
                f"{error_message.error_description}"
                f"\nBe aware that the robot may still be moving even though a stop has "
                "been attempted"
            )

            return True
        time.sleep(self.state_machine.sleep_time)
        return False
