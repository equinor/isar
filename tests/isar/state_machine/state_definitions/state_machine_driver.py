import json
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import pytest

from isar.models.events import APIEvent, EmptyMessage, Event, Events, RobotActionEvent
from isar.state_machine import state as state_module
from isar.state_machine.state import State, StateDef
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states_enum import States


@dataclass(frozen=True)
class Outputs:
    api_responses: dict[str, Any]
    robot_requests: dict[str, Any]
    mqtt: list[dict[str, Any]]


class _Clock:
    """Stands in for the time module in state.py. Sleeping ends State.run after one iteration."""

    def __init__(self, signal_exit: Event[EmptyMessage]) -> None:
        self._now = 0.0
        self._pending = 0.0
        self._signal_exit = signal_exit

    def elapse_after_entry(self, seconds: float) -> None:
        self._pending = seconds

    def time(self) -> float:
        now = self._now
        self._now += self._pending
        self._pending = 0.0
        return now

    def sleep(self, _: float) -> None:
        self._signal_exit.trigger_event(EmptyMessage())


class StateMachineDriver:
    """Drives a real StateMachine one event at a time and records what it outputs."""

    def __init__(self, machine: StateMachine, clock: _Clock) -> None:
        self.machine = machine
        self.events = machine.events
        self._clock = clock

    @property
    def state(self) -> State:
        return self.machine.current_state

    def enter(self, state_def: StateDef[Any], param: Any = None) -> None:
        # Built directly so that no transition side effects run before the step under test
        self.machine.current_state = State(
            state_def,
            param,
            self.events,
            self.machine._output_events,
            self.machine.signal_exit,
        )

    def send[T](self, event: Event[T], message: T) -> States:
        event.trigger_event(message)
        return self.step()

    def step(self, elapsed_seconds: float = 0.0) -> States:
        self.machine.signal_exit.clear_event()
        self._clock.elapse_after_entry(elapsed_seconds)
        transition = self.state.run()
        if transition is not None:
            self.machine.current_state = self.machine._enter(transition)
        return self.state.name

    def outputs(self) -> Outputs:
        """Returns and clears everything the state machine has sent out."""
        api_responses = {
            name: api_event.response.consume_event()
            for name, api_event in vars(self.events.api_requests).items()
            if isinstance(api_event, APIEvent) and api_event.response.has_event()
        }
        robot_requests = {
            name: action.request.consume_event()
            for name, action in vars(self.events.action_requests).items()
            if isinstance(action, RobotActionEvent) and action.request.has_event()
        }
        mqtt: list[dict[str, Any]] = []
        while (message := self.events.mqtt_queue.get()) is not None:
            mqtt.append(json.loads(message.payload))
        return Outputs(api_responses, robot_requests, mqtt)


@pytest.fixture()
def state_machine_driver(
    events: Events, monkeypatch: pytest.MonkeyPatch
) -> Generator[StateMachineDriver]:
    machine = StateMachine(events, events.mqtt_queue)
    clock = _Clock(machine.signal_exit)
    monkeypatch.setattr(state_module, "time", clock)
    yield StateMachineDriver(machine, clock)
