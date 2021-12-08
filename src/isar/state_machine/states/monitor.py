import logging
import time
from typing import TYPE_CHECKING

from injector import inject
from transitions import State

from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
    ThreadedRequestUnexpectedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission import DriveToPose, TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):
    @inject
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="monitor", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")

        self.iteration_counter: int = 0
        self.log_interval = 20

        self.task_status_thread = None

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.current_state}")

        self._run()

    def stop(self):
        self.iteration_counter = 0
        if self.task_status_thread:
            self.task_status_thread.wait_for_thread()
        self.task_status_thread = None

    def _run(self):
        while True:
            if self.state_machine.should_stop_mission():
                self.state_machine.stop_mission()

            if not self.state_machine.mission_in_progress:
                next_state = States.Cancel
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()
            if not self.task_status_thread:
                self.task_status_thread = ThreadedRequest(
                    self.state_machine.robot.task_status
                )
                self.task_status_thread.start_thread(self.state_machine.current_task.id)

            try:
                task_status = self.task_status_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except ThreadedRequestUnexpectedError:
                task_status = TaskStatus.Unexpected

            self.state_machine.current_task.status = task_status

            self._log_status()

            if self._task_completed(task_status=self.state_machine.current_task.status):
                if isinstance(self.state_machine.current_task, DriveToPose):

                    next_state = States.Send
                else:
                    next_state = States.Collect
                break
            else:
                self.task_status_thread = None
                time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)

    def _task_completed(self, task_status: TaskStatus) -> bool:

        if task_status == TaskStatus.Unexpected:
            self.logger.error("Task status returned an unexpected status string")
        elif task_status == TaskStatus.Failed:
            self.logger.warning("Task failed...")
            return True
        elif task_status == TaskStatus.Completed:
            return True
        return False

    def _log_status(self):
        if self.iteration_counter % self.log_interval == 0:
            self.state_machine.robot.log_status(
                task_status=self.state_machine.current_task.status,
                current_task=self.state_machine.current_task,
            )
        self.iteration_counter += 1
