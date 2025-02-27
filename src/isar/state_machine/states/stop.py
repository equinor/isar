import logging
import time
from queue import Queue
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.models.communication.queues.queue_utils import check_for_event
from isar.services.utilities.threaded_request import ThreadedRequest

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stop(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="stop", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = self.state_machine.events
        self.stop_thread: Optional[ThreadedRequest] = None
        self._count_number_retries: int = 0

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        if self.stop_thread:
            self.stop_thread.wait_for_thread()
        self.stop_thread = None
        self._count_number_retries = 0

    def _check_and_handle_failed_stop(self, event: Queue) -> bool:
        error_message = check_for_event(event)
        if error_message is not None:
            self.logger.warning(error_message)
            self.state_machine.mission_stopped()  # type: ignore
            return True
        return False

    def _check_and_handle_successful_stop(self, event: Queue) -> bool:
        if check_for_event(event):
            self.state_machine.mission_stopped()  # type: ignore
            return True
        return False

    def _run(self) -> None:
        while True:

            if self._check_and_handle_failed_stop(
                self.events.robot_service_events.mission_failed_to_stop
            ):
                break

            if self._check_and_handle_successful_stop(
                self.events.robot_service_events.mission_successfully_stopped
            ):
                break

            time.sleep(self.state_machine.sleep_time)
