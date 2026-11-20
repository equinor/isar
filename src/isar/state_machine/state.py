import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events
from isar.state_machine.states_enum import States


class HandlerEffect[StateParam, EventType]:
    """Sends a value to the event selected by target when its branch is taken."""

    # T only exists in the constructor, so that the type of value is checked against
    # target when the effect is created, but is not needed when effects are grouped.
    def __init__[T](
        self,
        target: Callable[[Events], Callable[[T], None]],
        value: Callable[[StateParam, EventType], T],
        when: Callable[[StateParam, EventType], bool] = lambda _, __: True,
    ) -> None:
        self.target: Callable[[Events], Callable[[Any], None]] = target
        self.value: Callable[[StateParam, EventType], Any] = value
        self.when = when

    def run(self, events: Events, param: StateParam, event_value: EventType) -> None:
        if self.when(param, event_value):
            self.target(events)(self.value(param, event_value))


class TransitionEffect[TransitionParam]:
    """Sends a value to the event selected by target when the transition is entered."""

    def __init__[T](
        self,
        target: Callable[[Events], Callable[[T], None]],
        value: Callable[[TransitionParam], T],
    ) -> None:
        self.target: Callable[[Events], Callable[[Any], None]] = target
        self.value: Callable[[TransitionParam], Any] = value

    def run(self, events: Events, transition_input: TransitionParam) -> None:
        self.target(events)(self.value(transition_input))


class ClearEvent(TransitionEffect[Any]):
    """Discards anything waiting in the selected event when the transition is entered."""

    def __init__(self, select: Callable[[Events], Event[Any]]) -> None:
        def clear(events: Events) -> Callable[[None], None]:
            def run(_: None) -> None:
                select(events).clear_event()

            return run

        super().__init__(clear, lambda _: None)


def forward_transition_parameter[X](value: X) -> X:
    return value


def forward_state_parameter[StateParam](param: StateParam, _: object) -> StateParam:
    return param


def forward_event[EventType](_: object, msg: EventType) -> EventType:
    return msg


@dataclass(frozen=True)
class StateDef[StateParam]:
    name: States
    # Defined as functions to prevent circular dependencies between state modules
    handlers: Callable[[], tuple[EventHandler[StateParam, Any], ...]]
    timers: Callable[[], tuple[TimeoutHandler[StateParam], ...]] = lambda: ()


@dataclass(frozen=True)
class TransitionDef[TransitionParam, StateParam]:
    state_definition: StateDef[StateParam]
    state_param: Callable[[TransitionParam], StateParam] = lambda _: None
    effects: tuple[TransitionEffect[TransitionParam], ...] = ()

    def run_effects(self, events: Events, transition_input: TransitionParam) -> None:
        for effect in self.effects:
            effect.run(events, transition_input)


@dataclass(frozen=True)
class Branch[StateParam, EventType, TransitionParam]:
    transition: TransitionDef[TransitionParam, Any]
    transition_args: Callable[[StateParam, EventType], TransitionParam] = (
        lambda _, __: None
    )
    transition_when: Callable[[StateParam, EventType], bool] = lambda _, __: True
    effects: tuple[HandlerEffect[StateParam, EventType], ...] = ()

    def run_effects(
        self, events: Events, param: StateParam, event_value: EventType
    ) -> None:
        for effect in self.effects:
            effect.run(events, param, event_value)


@dataclass(frozen=True)
class EventHandler[StateParam, EventType]:
    event: Callable[[Events], Event[EventType]]
    # First matching branch is used. If none match then the event is ignored
    branches: tuple[Branch[StateParam, EventType, Any], ...]


@dataclass(frozen=True)
class TimeoutHandler[StateParam]:
    name: str
    timeout_in_seconds: float
    branches: tuple[Branch[StateParam, None, Any], ...]


@dataclass(frozen=True)
class Transition[TransitionParam]:
    transition_definition: TransitionDef[TransitionParam, Any]
    transition_input: TransitionParam


class State[StateParam]:
    def __init__(
        self,
        spec: StateDef[StateParam],
        param: StateParam,
        events: Events,
        signal_exit_event: Event[EmptyMessage] | None = None,
    ) -> None:
        self.name = spec.name
        self.param = param
        self.logger = logging.getLogger("state_machine")
        self.signal_exit_event = signal_exit_event
        self._events = events
        self._handlers = [
            (handler, handler.event(events)) for handler in spec.handlers()
        ]
        self._timers = spec.timers()

    def handles_event(self, event: Event) -> bool:
        return any(handled_event == event for _, handled_event in self._handlers)

    def run(self) -> Transition | None:
        pending_timers = list(self._timers)
        entered_time = time.time()
        while True:
            if (
                self.signal_exit_event is not None
                and self.signal_exit_event.has_event()
            ):
                self.logger.info("Stopping state machine from %s state", self.name.name)
                break

            for timer in list(pending_timers):
                if time.time() - entered_time > timer.timeout_in_seconds:
                    pending_timers.remove(timer)
                    self.logger.debug(f"Event timer '{timer.name}' triggered. ")
                    transition = self._select_branch_and_run_side_effect(
                        timer.branches, None
                    )
                    if transition is not None:
                        return transition

            for handler, event in self._handlers:
                event_value = event.consume_event()
                if event_value is not None:
                    self.logger.debug(
                        f"Event '{event.name}' triggered with input: {event_value}. "
                    )
                    transition = self._select_branch_and_run_side_effect(
                        handler.branches, event_value
                    )
                    if transition is not None:
                        return transition

            time.sleep(settings.FSM_SLEEP_TIME)
        return None

    def _select_branch_and_run_side_effect[T](
        self, branches: tuple[Branch[StateParam, T, Any], ...], event_value: T
    ) -> Transition | None:
        for branch in branches:
            if branch.transition_when(self.param, event_value):
                branch.run_effects(self._events, self.param, event_value)
                return Transition(
                    branch.transition, branch.transition_args(self.param, event_value)
                )
        return None
