import logging
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events
from isar.state_machine.states_enum import States

Transition = Callable[[Events], "StateDef"]


@dataclass
class EventHandlerMapping[T]:
    event: Event[T]
    handler: Callable[[T], Transition | None]


@dataclass
class TimeoutHandlerMapping:
    name: str
    timeout_in_seconds: float
    handler: Callable[[], Transition | None]


@dataclass
class StateDef:
    name: States
    handlers: list[EventHandlerMapping]
    timers: list[TimeoutHandlerMapping] | None = None


class State:
    def __init__(
        self,
        definition: StateDef,
        signal_exit_event: Event[EmptyMessage] | None = None,
    ) -> None:
        self.name = definition.name
        self.logger = logging.getLogger("state_machine")
        self.signal_exit_event = signal_exit_event
        self.handlers = definition.handlers
        self.timers = definition.timers if definition.timers is not None else []

    def get_event_handler_by_event(self, event: Event) -> EventHandlerMapping:
        filtered_handlers = [h for h in self.handlers if h.event == event]
        assert len(filtered_handlers) > 0
        return filtered_handlers[0]

    def get_event_timer_by_name(self, event_timer_name: str) -> TimeoutHandlerMapping:
        filtered_timers = [t for t in self.timers if t.name == event_timer_name]
        assert len(filtered_timers) > 0
        return filtered_timers[0]

    def handles_event(self, event: Event) -> bool:
        allowed_events: list[Event] = [m.event for m in self.handlers]
        return event in allowed_events

    def run(self) -> Transition | None:
        timers = deepcopy(self.timers)
        entered_time = time.time()
        while True:
            if self.signal_exit_event != None and self.signal_exit_event.has_event():
                self.logger.info("Stopping state machine from %s state", self.name.name)
                break

            for timer in timers:
                if time.time() - entered_time > timer.timeout_in_seconds:
                    transition = timer.handler()
                    timers.remove(timer)
                    self.logger.debug(f"Event timer '{timer.name}' triggered. ")
                    if transition is not None:
                        return transition

            for handler_mapping in self.handlers:
                event_value: Any | None = handler_mapping.event.consume_event()
                if event_value is not None:
                    transition = handler_mapping.handler(event_value)
                    self.logger.debug(
                        f"Event '{handler_mapping.event.name}' triggered with input: {event_value}. "
                    )
                    if transition is not None:
                        return transition

            time.sleep(settings.FSM_SLEEP_TIME)
        return None
