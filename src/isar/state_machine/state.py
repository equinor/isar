import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.states_enum import States

type HandlerSideEffect[P, T] = Callable[[OutputEvents, P, T], None]
type TransitionSideEffect[A] = Callable[[OutputEvents, A], None]


def forward[X](value: X) -> X:
    return value


def forward_state_parameter[P](param: P, _: object) -> P:
    return param


def forward_event[T](_: object, msg: T) -> T:
    return msg


@dataclass(frozen=True)
class StateDef[P]:
    name: States
    # Defined as functions to prevent circular dependencies between state modules
    handlers: Callable[[], tuple[EventHandler[P, Any], ...]]
    timers: Callable[[], tuple[TimeoutHandler[P], ...]] = lambda: ()


@dataclass(frozen=True)
class TransitionDef[A, P]:
    """A way of entering a state. A is the transition input, P is the state's parameter."""

    state_definition: StateDef[P]
    state_param: Callable[[A], P]
    side_effect: TransitionSideEffect[A] | None = None


@dataclass(frozen=True)
class Branch[P, T, A]:
    transition: TransitionDef[A, Any]
    transition_args: Callable[[P, T], A] = lambda _, __: None
    transition_when: Callable[[P, T], bool] = lambda _, __: True
    side_effect: HandlerSideEffect[P, T] | None = None


@dataclass(frozen=True)
class EventHandler[P, T]:
    event: Callable[[Events], Event[T]]
    # First matching branch wins; if none match then the event is ignored
    branches: tuple[Branch[P, T, Any], ...]


@dataclass(frozen=True)
class TimeoutHandler[P]:
    name: str
    timeout_in_seconds: float
    branches: tuple[Branch[P, None, Any], ...]


@dataclass(frozen=True)
class Transition[A]:
    transition_function: TransitionDef[A, Any]
    transition_input: A


class State[P]:
    def __init__(
        self,
        spec: StateDef[P],
        param: P,
        events: Events,
        handler_context: OutputEvents,
        signal_exit_event: Event[EmptyMessage] | None = None,
    ) -> None:
        self.name = spec.name
        self.param = param
        self.logger = logging.getLogger("state_machine")
        self.signal_exit_event = signal_exit_event
        self._handler_context = handler_context
        self._handlers = [(on, on.event(events)) for on in spec.handlers()]
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
        self, branches: tuple[Branch[P, T, Any], ...], event_value: T
    ) -> Transition | None:
        for branch in branches:
            if branch.transition_when(self.param, event_value):
                if branch.side_effect is not None:
                    branch.side_effect(self._handler_context, self.param, event_value)
                return Transition(
                    branch.transition, branch.transition_args(self.param, event_value)
                )
        return None
