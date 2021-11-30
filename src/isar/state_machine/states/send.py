import logging
import time
from typing import TYPE_CHECKING

from transitions import State

from isar.config import config
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
    ThreadedRequestUnexpectedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission import TakeImage, TakeThermalImage, Task
from robot_interface.models.mission.status import TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Send(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="send", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.send_failure_counter: int = 0
        self.send_failure_counter_limit: int = config.getint(
            "DEFAULT", "send_failure_counter_limit"
        )
        self.logger = logging.getLogger("state_machine")

        self.send_thread = None

    def start(self):
        self.state_machine.update_status()
        self.state_machine.update_current_task()
        self.logger.info(f"State: {self.state_machine.current_state}")

        self._run()

    def stop(self):
        self.send_failure_counter = 0
        if self.send_thread:
            self.send_thread.wait_for_thread()
        self.send_thread = None

    def _run(self):
        while True:
            if self.state_machine.should_stop_mission():
                self.state_machine.stop_mission()

            if not self.state_machine.mission_in_progress:
                next_state: States = States.Cancel
                break

            if not self.state_machine.current_task:
                next_state: States = States.Cancel
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()

            if not self.state_machine._check_dependencies():
                self.state_machine.current_task.status = TaskStatus.Failed
                self.logger.warning(
                    f"Dependancy for task {self.state_machine.current_task_index}: "
                    f"{self.state_machine.current_task.name}, not fulfilled, "
                    "skipping to next task"
                )
                next_state: States = States.Send
                break

            if not self.send_thread:
                self.send_thread = ThreadedRequest(
                    self.state_machine.robot.schedule_task
                )
                self.send_thread.start_thread(self.state_machine.current_task)

            try:
                send_success: bool = self.send_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except ThreadedRequestUnexpectedError:
                send_success = False

            if send_success:
                self.state_machine.current_task.status = TaskStatus.Scheduled
                next_state = States.Monitor
                break
            else:
                self.send_failure_counter += 1
                self.logger.info("sending failed #: " + str(self.send_failure_counter))
                if self.send_failure_counter >= self.send_failure_counter_limit:
                    self.logger.error(
                        f"Failed to send mission after "
                        f"{self.send_failure_counter_limit} attempts. "
                        f"Cancelling mission."
                    )
                    next_state: States = States.Cancel
                    break
                self.send_thread = None
                time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)
