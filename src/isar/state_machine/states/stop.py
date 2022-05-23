import logging
import time
from sqlite3 import enable_shared_cache
from typing import TYPE_CHECKING, Callable

from transitions import State

from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions import RobotException

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stop(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="stop", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.stop_thread = None

    def start(self):
        self.state_machine.update_state()
        self._run()

    def stop(self):
        if self.state_machine.mqtt_client:
            self.state_machine.publish_mission_status()
            self.state_machine.publish_task_status()
            self.state_machine.publish_step_status()

        self.iteration_counter = 0
        if self.stop_thread:
            self.stop_thread.wait_for_thread()
        self.step_status_thread = None

    def _run(self):
        transition: Callable
        while True:
            if not self.stop_thread:
                self.stop_thread = ThreadedRequest(self.state_machine.robot.stop)
                self.stop_thread.start_thread()

            try:
                self.stop_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotException:
                continue

            if self.state_machine.paused:
                transition = self.state_machine.paused_successfully
            else:
                transition = self.state_machine.finalize
            break

        transition()
