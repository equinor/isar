import logging
import time
from copy import deepcopy
from dataclasses import dataclass
from threading import Event as ThreadEvent
from typing import TYPE_CHECKING, Callable, Generic, List, Optional, TypeVar

from transitions import State

from isar.config.settings import settings
from isar.models.events import Event

T = TypeVar("T")


@dataclass
class EventHandlerMapping(Generic[T]):
    name: str
    event: Event[T]
    handler: Callable[[Event[T]], Optional[Callable]]


@dataclass
class TimeoutHandlerMapping:
    name: str
    timeout_in_seconds: float
    handler: Callable[[], Optional[Callable]]


if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class EventHandlerBase(State):
    def __init__(
        self,
        state_machine: "StateMachine",
        state_name: str,
        event_handler_mappings: List[EventHandlerMapping],
        timers: List[TimeoutHandlerMapping] = [],
    ) -> None:

        super().__init__(name=state_name, on_enter=self.start)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = state_machine.events
        self.signal_state_machine_to_stop: ThreadEvent = (
            state_machine.signal_state_machine_to_stop
        )
        self.event_handler_mappings = event_handler_mappings
        self.state_name: str = state_name
        self.timers = timers

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        return

    def get_event_handler_by_name(
        self, event_handler_name: str
    ) -> Optional[EventHandlerMapping]:
        filtered_handlers = list(
            filter(
                lambda mapping: mapping.name == event_handler_name,
                self.event_handler_mappings,
            )
        )
        return filtered_handlers[0] if len(filtered_handlers) > 0 else None

    def get_event_timer_by_name(
        self, event_timer_name: str
    ) -> Optional[TimeoutHandlerMapping]:
        filtered_timers = list(
            filter(
                lambda mapping: mapping.name == event_timer_name,
                self.timers,
            )
        )
        return filtered_timers[0] if len(filtered_timers) > 0 else None

    def _run(self) -> None:
        should_exit_state: bool = False
        timers = deepcopy(self.timers)
        entered_time = time.time()
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.state_name
                )
                break

            for timer in timers:
                if time.time() - entered_time > timer.timeout_in_seconds:
                    transition_func = timer.handler()
                    timers.remove(timer)
                    if transition_func is not None:
                        transition_func()
                        should_exit_state = True
                        break

            if should_exit_state:
                break

            for handler_mapping in self.event_handler_mappings:
                transition_func = handler_mapping.handler(handler_mapping.event)
                if transition_func is not None:
                    transition_func()
                    should_exit_state = True
                    break

            if should_exit_state:
                break
            time.sleep(settings.FSM_SLEEP_TIME)
