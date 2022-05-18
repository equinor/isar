import logging
import time
from typing import TYPE_CHECKING

from transitions import State

from isar.config.settings import settings
from isar.models.mission.status import MissionStatus
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions import (
    RobotException,
    RobotInfeasibleStepException,
)
from robot_interface.models.mission.status import StepStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class InitiateStep(State):
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="initiate_step", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.initiate_step_failure_counter: int = 0
        self.initiate_step_failure_counter_limit: int = (
            settings.INITIATE_STEP_FAILURE_COUNTER_LIMIT
        )
        self.logger = logging.getLogger("state_machine")

        self.initiate_step_thread = None

    def start(self):
        self.state_machine.update_state()
        self.state_machine.update_current_task()
        self.state_machine.update_current_step()

        if self.state_machine.mqtt_client:
            self.state_machine.publish_step_status()

        self._run()

    def stop(self):
        if self.state_machine.mqtt_client:
            self.state_machine.publish_step_status()

        self.initiate_step_failure_counter = 0
        if self.initiate_step_thread:
            self.initiate_step_thread.wait_for_thread()
        self.initiate_step_thread = None

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

            if not self.initiate_step_thread:
                self.initiate_step_thread = ThreadedRequest(
                    self.state_machine.robot.initiate_step
                )
                self.initiate_step_thread.start_thread(self.state_machine.current_step)

            try:
                self.initiate_step_thread.get_output()
                initiate_step_success = True
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotInfeasibleStepException:
                self.state_machine.current_step.status = StepStatus.Failed
                self.logger.warning(
                    f"Failed to initiate "
                    f"{type(self.state_machine.current_step).__name__}"
                    f"Invalid step: {str(self.state_machine.current_step.id)[:8]}"
                )
                next_state = States.InitiateStep
                break
            except RobotException:
                initiate_step_success = False

            if initiate_step_success:
                self.state_machine.current_step.status = StepStatus.InProgress
                next_state = States.Monitor
                self.logger.info(
                    f"Successfully initiated "
                    f"{type(self.state_machine.current_step).__name__} "
                    f"step: {str(self.state_machine.current_step.id)[:8]}"
                )
                break
            else:
                self.initiate_step_failure_counter += 1
                self.logger.info(
                    f"Initiating step failed #: "
                    f"{str(self.initiate_step_failure_counter)}"
                )
                if (
                    self.initiate_step_failure_counter
                    >= self.initiate_step_failure_counter_limit
                ):
                    self.state_machine.current_step.status = StepStatus.Failed
                    self.state_machine.current_mission.status = MissionStatus.Failed
                    self.logger.error(
                        f"Failed to initiate step after "
                        f"{self.initiate_step_failure_counter_limit} attempts. "
                        f"Cancelling mission."
                    )
                    next_state: States = States.Finalize
                    break
                self.initiate_step_thread = None
                time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)
