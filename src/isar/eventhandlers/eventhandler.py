import logging
import time
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass
from threading import Event as ThreadEvent
from typing import TYPE_CHECKING, Any, Callable, Generic, List, Optional, TypeVar

from isar.config.settings import settings
from isar.models.events import Event
from isar.state_machine.states_enum import States

T = TypeVar("T")

T_state = TypeVar("T_state", bound="State", covariant=True)
Transition = Callable[["StateMachine"], T_state]


@dataclass
class EventHandlerMapping(Generic[T]):
    name: str
    event: Event[T]
    handler: Callable[[T], Optional[Transition]]
    should_not_consume: bool = False


@dataclass
class TimeoutHandlerMapping:
    name: str
    timeout_in_seconds: float
    handler: Callable[[], Optional[Callable]]


if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class State(ABC):
    def __init__(
        self,
        state_machine: "StateMachine",
        state_name: States,
        event_handler_mappings: List[EventHandlerMapping],
        timers: List[TimeoutHandlerMapping] = [],
    ) -> None:
        self.name = state_name
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = state_machine.events
        self.signal_state_machine_to_stop: ThreadEvent = (
            state_machine.signal_state_machine_to_stop
        )
        self.event_handler_mappings = event_handler_mappings
        self.timers = timers

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

    def run(self) -> Optional["State"]:
        should_exit_state: bool = False
        timers = deepcopy(self.timers)
        entered_time = time.time()
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info("Stopping state machine from %s state", self.name)
                break

            for timer in timers:
                if time.time() - entered_time > timer.timeout_in_seconds:
                    transition = timer.handler()
                    timers.remove(timer)
                    if transition is not None:
                        return transition(self.state_machine)

            if should_exit_state:
                break

            for handler_mapping in self.event_handler_mappings:
                event_value: Optional[Any]
                if handler_mapping.should_not_consume:
                    event_value = handler_mapping.event.check()
                else:
                    event_value = handler_mapping.event.consume_event()
                if event_value is not None:
                    transition = handler_mapping.handler(event_value)
                    if transition is not None:
                        return transition(self.state_machine)

            if should_exit_state:
                break
            time.sleep(settings.FSM_SLEEP_TIME)
        return None
