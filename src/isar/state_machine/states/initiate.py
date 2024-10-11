import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

from transitions import State

from isar.config.settings import settings
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotInfeasibleMissionException,
    RobotInfeasibleTaskException,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Initiate(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="initiate", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.initiate_failure_counter: int = 0
        self.initiate_failure_counter_limit: int = (
            settings.INITIATE_FAILURE_COUNTER_LIMIT
        )
        self.logger = logging.getLogger("state_machine")

        self.initiate_thread: Optional[ThreadedRequest] = None

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        self.initiate_failure_counter = 0
        if self.initiate_thread:
            self.initiate_thread.wait_for_thread()
        self.initiate_thread = None

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

            if not self.initiate_thread:
                if self.state_machine.run_mission_by_task:
                    self._run_initiate_thread(
                        initiate_function=self.state_machine.robot.initiate_task,
                        function_argument=self.state_machine.current_task,
                        thread_name="State Machine Initiate Task",
                    )
                else:
                    self._run_initiate_thread(
                        initiate_function=self.state_machine.robot.initiate_mission,
                        function_argument=self.state_machine.current_mission,
                        thread_name="State Machine Initiate Mission",
                    )

            try:
                self.initiate_thread.get_output()
                transition = self.state_machine.initiated  # type: ignore
                break
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotInfeasibleTaskException as e:
                self.state_machine.current_task.error_message = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                self.logger.warning(
                    f"Failed to initiate task "
                    f"{str(self.state_machine.current_task.id)[:8]} after retrying "
                    f"{self.initiate_failure_counter} times because: "
                    f"{e.error_description}"
                )
                transition = self.state_machine.initiate_infeasible  # type: ignore
                break

            except RobotInfeasibleMissionException as e:
                self.state_machine.current_mission.error_message = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                self.logger.warning(
                    f"Failed to initiate mission "
                    f"{str(self.state_machine.current_mission.id)[:8]} because: "
                    f"{e.error_description}"
                )
                transition = self.state_machine.initiate_failed  # type: ignore
                break

            except RobotException as e:
                self.initiate_thread = None
                self.initiate_failure_counter += 1
                self.logger.warning(
                    f"Initiating failed #: {str(self.initiate_failure_counter)} "
                    f"because: {e.error_description}"
                )

                if self.initiate_failure_counter >= self.initiate_failure_counter_limit:
                    self.state_machine.current_task.error_message = ErrorMessage(
                        error_reason=e.error_reason,
                        error_description=e.error_description,
                    )
                    self.logger.error(
                        f"Mission will be cancelled after failing to initiate "
                        f"{self.initiate_failure_counter_limit} times because: "
                        f"{e.error_description}"
                    )
                    transition = self.state_machine.initiate_failed  # type: ignore
                    break

            time.sleep(self.state_machine.sleep_time)

        transition()

    def _run_initiate_thread(
        self, initiate_function: Callable, function_argument: Any, thread_name: str
    ) -> None:
        self.initiate_thread = ThreadedRequest(request_func=initiate_function)

        self.initiate_thread.start_thread(
            function_argument,
            name=thread_name,
        )
