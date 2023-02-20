import logging
import time
from typing import Callable, Optional, TYPE_CHECKING

from transitions import State

from isar.config.settings import settings
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions import (
    RobotException,
    RobotInfeasibleStepException,
    RobotLowBatteryException,
)


if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class InitiateStep(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="initiate_step", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.initiate_step_failure_counter: int = 0
        self.initiate_step_failure_counter_limit: int = (
            settings.INITIATE_STEP_FAILURE_COUNTER_LIMIT
        )
        self.logger = logging.getLogger("state_machine")

        self.initiate_step_thread: Optional[ThreadedRequest] = None

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        self.initiate_step_failure_counter = 0
        if self.initiate_step_thread:
            self.initiate_step_thread.wait_for_thread()
        self.initiate_step_thread = None

    def _run(self) -> None:
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop  # type: ignore
                break

            if self.state_machine.should_pause_mission():
                transition = self.state_machine.pause  # type: ignore
                break

            if not self.state_machine.current_task:
                self.logger.info(
                    f"Completed mission: {self.state_machine.current_mission.id}"
                )
                transition = self.state_machine.mission_finished  # type: ignore
                break

            if not self.initiate_step_thread:
                self.initiate_step_thread = ThreadedRequest(
                    self.state_machine.robot.initiate_step
                )
                self.initiate_step_thread.start_thread(
                    self.state_machine.current_step,
                    name="State Machine Initiate Step",
                )

            try:
                self.initiate_step_thread.get_output()
                transition = self.state_machine.step_initiated  # type: ignore
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
                transition = self.state_machine.step_infeasible  # type: ignore
                break

            except RobotLowBatteryException as e:
                self.logger.warning(
                    f"Battery too low to perform step"
                    f"{type(self.state_machine.current_step).__name__}"
                    f"Current Battery Level: {str(e.battery_level)}"
                )
                transition = self.state_machine.initiate_step_failed  # type: ignore
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
                transition = self.state_machine.initiate_step_failed  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
