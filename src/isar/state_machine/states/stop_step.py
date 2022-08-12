import logging
import time
from typing import TYPE_CHECKING, Callable

from transitions import State

from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions import RobotException

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StopStep(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="stop_step", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.stop_thread = None
        self._count_number_retries = 0
        self._lost_connection_robot = False

    def start(self):
        self.state_machine.update_state()
        self._run()

    def stop(self):
        if self.stop_thread:
            self.stop_thread.wait_for_thread()
        self.stop_thread = None

    def _run(self):
        transition: Callable
        while True:
            if not self.stop_thread:
                self.stop_thread = ThreadedRequest(self.state_machine.robot.stop)
                self.stop_thread.start_thread()

            if self.state_machine.should_stop_mission():
                self.state_machine.stopped = True

            try:
                self.stop_thread.get_output()
            except ThreadedRequestNotFinishedError:
                if self._lost_connection_robot:
                    transition = self.state_machine.mission_stopped
                    self.logger.warning(
                        "Could not communicate request: Reached limit for stop attemps. Cancelled mission and transitioned to idle."
                    )
                    break
                else:
                    self.logger.info("Attempting to stop mission.")
                    self.handle_stop_fail(retry_limit=50)
                    time.sleep(self.state_machine.sleep_time)
                    continue

            except RobotException:
                self.logger.warning("Failed to stop robot. Retrying.")
                self.stop_thread = None
                continue
            if self.state_machine.stopped:
                transition = self.state_machine.mission_stopped
            else:
                transition = self.state_machine.mission_paused
            break

        transition()

    def handle_stop_fail(self, retry_limit: int):
        self._count_number_retries += 1
        if self._count_number_retries > retry_limit:
            self._lost_connection_robot = True
