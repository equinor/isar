import logging
import time
from typing import TYPE_CHECKING, Callable

from transitions import State

from isar.models.communication.queues.queue_utils import check_for_event

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Paused(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="paused", on_enter=self.start)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = self.state_machine.events
        self.signal_state_machine_to_stop = state_machine.signal_state_machine_to_stop

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def _run(self) -> None:
        transition: Callable
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.__class__.__name__
                )
                break

            if check_for_event(self.events.api_requests.pause_mission.input):
                transition = self.state_machine.stop  # type: ignore
                break

            if check_for_event(self.events.api_requests.resume_mission.input):
                transition = self.state_machine.resume  # type: ignore
                break

            time.sleep(self.state_machine.sleep_time)

        transition()
