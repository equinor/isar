import logging
import time
from dataclasses import dataclass
from queue import Queue
from threading import Event
from typing import TYPE_CHECKING, Callable, List

from transitions import State

from isar.config.settings import settings


@dataclass
class EventHandlerMapping:
    name: str
    eventQueue: Queue
    handler: Callable[[Queue], Callable | None]


if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class EventHandlerBase(State):
    def __init__(
        self,
        state_machine: "StateMachine",
        state_name: str,
        event_handler_mappings: List[EventHandlerMapping],
    ) -> None:
        super().__init__(name=state_name, on_enter=self.start)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = state_machine.events
        self.signal_state_machine_to_stop: Event = (
            state_machine.signal_state_machine_to_stop
        )
        self.event_handler_mappings = event_handler_mappings
        self.state_name: str = state_name

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        return

    def _run(self) -> None:
        should_transition: bool = False
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.state_name
                )
                break

            for handler_mapping in self.event_handler_mappings:
                transition_func = handler_mapping.handler(handler_mapping.eventQueue)
                if transition_func is not None:
                    transition_func()
                    should_transition = True
                    break
            if should_transition:
                break
            time.sleep(settings.FSM_SLEEP_TIME)
