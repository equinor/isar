import logging
import time
from typing import TYPE_CHECKING, Callable

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
        self._run()

    def stop(self):
        self.initiate_step_failure_counter = 0
        if self.initiate_step_thread:
            self.initiate_step_thread.wait_for_thread()
        self.initiate_step_thread = None

    def _run(self):
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop
                break

            if self.state_machine.should_pause_mission():
                transition = self.state_machine.pause
                break

            if not self.state_machine.current_task:
                self.logger.info(
                    f"Completed mission: {self.state_machine.current_mission.id}"
                )
                transition = self.state_machine.mission_finished
                break

            if not self.initiate_step_thread:
                self.initiate_step_thread = ThreadedRequest(
                    self.state_machine.robot.initiate_step
                )
                self.initiate_step_thread.start_thread(self.state_machine.current_step)

            try:
                self.initiate_step_thread.get_output()
                transition = self.state_machine.step_initiated
                break
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotInfeasibleStepException:
                self.logger.warning(
                    f"Failed to initiate "
                    f"{type(self.state_machine.current_step).__name__}"
                    f"Invalid step: {str(self.state_machine.current_step.id)[:8]}"
                )
                transition = self.state_machine.step_infeasible
                break
            except RobotException as e:
                self.initiate_step_thread = None
                self.initiate_step_failure_counter += 1
                self.logger.warning(
                    f"Initiating step failed #: "
                    f"{str(self.initiate_step_failure_counter)}"
                    f"{e}"
                )

            if (
                self.initiate_step_failure_counter
                >= self.initiate_step_failure_counter_limit
            ):
                self.logger.error(
                    f"Failed to initiate step after "
                    f"{self.initiate_step_failure_counter_limit} attempts. "
                    f"Cancelling mission."
                )
                transition = self.state_machine.initiate_step_failed
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
