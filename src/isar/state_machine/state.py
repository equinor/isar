import logging
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Concatenate, ParamSpec

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events, _get_events_hash
from isar.state_machine.states_enum import States

Transition = Callable[[Events], "StateDef"]

states_list: list[str] = []

P = ParamSpec("P")


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


def state_definition[**P](
    state_func: Callable[Concatenate[Events, P], StateDef],
) -> Callable[Concatenate[Events, P], StateDef]:
    state_name: str = state_func.__name__
    assert state_name in (
        state.name for state in States
    ), f"{state_name} needs to be added to the States enum"
    states_list.append(state_name)

    def wrapper(events: Events, *args: P.args, **kwargs: P.kwargs) -> StateDef:
        events_hash = _get_events_hash(events)
        state_def = state_func(events, *args, **kwargs)
        assert (
            _get_events_hash(events) == events_hash
        ), f"{state_name} has side effects in its definition"

        assert len(state_def.handlers) > 0, f"{state_name} is missing eventhandlers"

        event_set = set()
        for handler in state_def.handlers:
            assert (
                not handler.event in event_set
            ), f"{state_name} has two handlers for event '{handler.event.name}'"
            event_set.add(handler.event)

        for timer in state_def.timers if state_def.timers is not None else []:
            assert (
                timer.timeout_in_seconds >= 0.0
            ), f"Timer {timer.name} in state {state_name} has a negative timeout"
        return state_def

    return wrapper


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
