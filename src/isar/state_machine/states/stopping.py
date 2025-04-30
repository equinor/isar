import logging
import time
from queue import Queue
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.models.communication.queues.queue_utils import check_for_event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stopping(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="stopping", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = self.state_machine.events
        self._count_number_retries: int = 0
        self.signal_state_machine_to_stop = state_machine.signal_state_machine_to_stop
        self.stopping_return_home_mission: bool = False

    def start(self) -> None:
        self.state_machine.update_state()
        if self.state_machine.current_mission is not None:
            self.stopping_return_home_mission = (
                self.state_machine.current_mission._is_return_to_home_mission()
            )
        self._run()

    def stop(self) -> None:
        self._count_number_retries = 0
        self.stopping_return_home_mission = False

    def _check_and_handle_failed_stop(self, event: Queue[ErrorMessage]) -> bool:
        error_message: Optional[ErrorMessage] = check_for_event(event)
        if error_message is not None:
            self.logger.warning(error_message.error_description)
            if self.stopping_return_home_mission:
                self.state_machine.return_home_mission_stopped()  # type: ignore
            else:
                self.state_machine.mission_stopped()  # type: ignore
            return True
        return False

    def _check_and_handle_successful_stop(self, event: Queue[bool]) -> bool:
        if check_for_event(event):
            if self.stopping_return_home_mission:
                self.state_machine.return_home_mission_stopped()  # type: ignore
            else:
                self.state_machine.mission_stopped()  # type: ignore
            return True
        return False

    def _run(self) -> None:
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.__class__.__name__
                )
                break

            if self._check_and_handle_failed_stop(
                self.events.robot_service_events.mission_failed_to_stop
            ):
                break

            if self._check_and_handle_successful_stop(
                self.events.robot_service_events.mission_successfully_stopped
            ):
                break

            time.sleep(self.state_machine.sleep_time)
