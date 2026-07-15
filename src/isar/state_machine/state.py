import logging
import time
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Generic, List, TypeVar

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events
from isar.state_machine.states_enum import States

T = TypeVar("T")

T_state = TypeVar("T_state", bound="State", covariant=True)
Transition = Callable[[Events], T_state]


@dataclass
class EventHandlerMapping(Generic[T]):
    name: str
    event: Event[T]
    handler: Callable[[T], Transition | None]


@dataclass
class TimeoutHandlerMapping:
    name: str
    timeout_in_seconds: float
    handler: Callable[[], Transition | None]


class State(ABC):
    def __init__(
        self,
        signal_exit_event: Event[EmptyMessage],
        state_name: States,
        event_handler_mappings: List[EventHandlerMapping],
        timers: List[TimeoutHandlerMapping] = [],
    ) -> None:
        self.name = state_name
        self.logger = logging.getLogger("state_machine")
        self.signal_exit_event = signal_exit_event
        self.event_handler_mappings = event_handler_mappings
        self.timers = timers

    def get_event_handler_by_name(
        self, event_handler_name: str
    ) -> EventHandlerMapping | None:
        filtered_handlers = list(
            filter(
                lambda mapping: mapping.name == event_handler_name,
                self.event_handler_mappings,
            )
        )
        return filtered_handlers[0] if len(filtered_handlers) > 0 else None

    def get_event_timer_by_name(
        self, event_timer_name: str
    ) -> TimeoutHandlerMapping | None:
        filtered_timers = list(
            filter(
                lambda mapping: mapping.name == event_timer_name,
                self.timers,
            )
        )
        return filtered_timers[0] if len(filtered_timers) > 0 else None

    def run(self) -> Transition | None:
        timers = deepcopy(self.timers)
        entered_time = time.time()
        while True:
            if self.signal_exit_event.has_event():
                self.logger.info("Stopping state machine from %s state", self.name)
                break

            for timer in timers:
                if time.time() - entered_time > timer.timeout_in_seconds:
                    transition = timer.handler()
                    timers.remove(timer)
                    if transition is not None:
                        return transition

            for handler_mapping in self.event_handler_mappings:
                event_value: Any | None = handler_mapping.event.consume_event()
                if event_value is not None:
                    transition = handler_mapping.handler(event_value)
                    if transition is not None:
                        self.logger.debug(
                            f"Event '{handler_mapping.name}' triggered with input: {event_value}. "
                        )
                        self.logger.debug(
                            f"Transitioning from {self.name.name} to {transition.__annotations__['return'].__name__}"
                        )
                        return transition

            time.sleep(settings.FSM_SLEEP_TIME)
        return None
