"""Ordering rules over every path through the state machine, using the outputs observed in the behaviour cases."""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from isar.config.settings import settings
from isar.models.events import Event, Events
from isar.state_machine.state_machine import collect_edges
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus
from tests.isar.state_machine.state_definitions.state_machine_driver import (
    MqttMessage,
    Outputs,
    StateMachineDriver,
)
from tests.isar.state_machine.state_definitions.test_state_behaviour import all_cases


@dataclass(frozen=True)
class ObservedEdge:
    source: States
    trigger: str
    target: States
    outputs: Outputs


def observed_edges(events: Events, driver: StateMachineDriver) -> list[ObservedEdge]:
    edges = []
    for case in all_cases(events):
        driver.enter(case.start, case.param)
        target = driver.send(case.event, case.expect.message)
        edges.append(
            ObservedEdge(case.start.name, case.event.name, target, driver.outputs())
        )
    return edges


def find_invalid_transition_path(
    edges: list[ObservedEdge],
    start: States,
    forbidden: Callable[[ObservedEdge], bool],
    satisfied_by: Callable[[ObservedEdge], bool],
) -> list[ObservedEdge] | None:
    """A path from start to a forbidden edge that never passes an edge satisfying the requirement."""
    frontier: list[tuple[States, list[ObservedEdge]]] = [(start, [])]
    seen = {start}
    while frontier:
        state, path = frontier.pop()
        for edge in edges:
            if edge.source != state or satisfied_by(edge):
                continue
            if forbidden(edge):
                return [*path, edge]
            if edge.target not in seen:
                seen.add(edge.target)
                frontier.append((edge.target, [*path, edge]))
    return None


def describe(path: list[ObservedEdge]) -> str:
    return " -> ".join(f"{e.source.name} [{e.trigger}]" for e in path)


def test_behaviour_cases_cover_every_branch(
    events: Events, state_machine_driver: StateMachineDriver
) -> None:
    observed = {
        (e.source, e.trigger, e.target)
        for e in observed_edges(events, state_machine_driver)
    }
    # Timer branches are not driven by an event, so they are tested separately
    declared = {
        (e.source, e.trigger.name, e.target)
        for e in collect_edges(events)
        if isinstance(e.trigger, Event)
    }
    assert declared <= observed, sorted(declared - observed)


def reports_mission_result(message: MqttMessage) -> bool:
    # Aborted missions are reported on their own topic, without a mission status
    if message.topic == settings.TOPIC_ISAR_MISSION_ABORTED:
        return True
    return message.topic.startswith(
        settings.TOPIC_ISAR_MISSION + "/"
    ) and message.payload["status"] in (
        MissionStatus.Successful,
        MissionStatus.Failed,
        MissionStatus.Cancelled,
    )


def test_mission_result_is_reported_before_a_new_mission_starts(
    events: Events, state_machine_driver: StateMachineDriver
) -> None:
    path = find_invalid_transition_path(
        observed_edges(events, state_machine_driver),
        start=States.Monitor,
        forbidden=lambda e: e.trigger == events.api_requests.start_mission.request.name,
        satisfied_by=lambda e: any(reports_mission_result(m) for m in e.outputs.mqtt),
    )
    if path is not None:
        pytest.fail(describe(path))
