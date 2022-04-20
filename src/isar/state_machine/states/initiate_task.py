import logging
import time
from typing import TYPE_CHECKING

from transitions import State

from isar.config.settings import settings
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions import (
    RobotException,
    RobotInfeasibleTaskException,
)
from robot_interface.models.mission.status import TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class InitiateTask(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="initiate_task", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.initiate_task_failure_counter: int = 0
        self.initiate_task_failure_counter_limit: int = (
            settings.INITIATE_TASK_FAILURE_COUNTER_LIMIT
        )
        self.logger = logging.getLogger("state_machine")

        self.initiate_task_thread = None

    def start(self):
        self.state_machine.update_state()
        self.state_machine.update_current_task()

        if self.state_machine.mqtt_client:
            self.state_machine.publish_task_status()
            self.state_machine.publish_mission()

        self._run()

    def stop(self):
        if self.state_machine.mqtt_client:
            self.state_machine.publish_task_status()
            self.state_machine.publish_mission()

        self.initiate_task_failure_counter = 0
        if self.initiate_task_thread:
            self.initiate_task_thread.wait_for_thread()
        self.initiate_task_thread = None

    def _run(self):
        while True:
            if self.state_machine.should_stop_mission():
                self.state_machine.stop_mission()

            if not self.state_machine.mission_in_progress:
                next_state: States = States.Finalize
                break

            if not self.state_machine.current_task:
                next_state: States = States.Finalize
                self.logger.info(
                    f"Completed mission: {self.state_machine.current_mission.id}"
                )
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()

            if not self.state_machine._check_dependencies():
                self.state_machine.current_task.status = TaskStatus.Failed
                self.logger.warning(
                    f"Dependency for task {self.state_machine.current_task_index}: "
                    f"{self.state_machine.current_task.type}, not fulfilled, "
                    "skipping to next task"
                )

                next_state: States = States.InitiateTask
                break

            if not self.initiate_task_thread:
                self.initiate_task_thread = ThreadedRequest(
                    self.state_machine.robot.initiate_task
                )
                self.initiate_task_thread.start_thread(self.state_machine.current_task)

            try:
                self.initiate_task_thread.get_output()
                initiate_task_success = True
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue

            except RobotInfeasibleTaskException:
                self.state_machine.current_task.status = TaskStatus.Failed
                self.logger.warning(
                    f"Failed to initiate {type(self.state_machine.current_task).__name__}"
                    f"Invalid task: {str(self.state_machine.current_task.id)[:8]}"
                )
                next_state = States.InitiateTask
                break
            except RobotException:
                initiate_task_success = False

            if initiate_task_success:
                self.state_machine.current_task.status = TaskStatus.Scheduled
                next_state = States.Monitor
                self.logger.info(
                    f"Successfully initiated {type(self.state_machine.current_task).__name__} "
                    f"task: {str(self.state_machine.current_task.id)[:8]}"
                )
                break
            else:
                self.initiate_task_failure_counter += 1
                self.logger.info(
                    f"Initiating task failed #: {str(self.initiate_task_failure_counter)}"
                )
                if (
                    self.initiate_task_failure_counter
                    >= self.initiate_task_failure_counter_limit
                ):
                    self.logger.error(
                        f"Failed to initiate task after "
                        f"{self.initiate_task_failure_counter_limit} attempts. "
                        f"Cancelling mission."
                    )
                    next_state: States = States.Finalize
                    break
                self.initiate_task_thread = None
                time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)
