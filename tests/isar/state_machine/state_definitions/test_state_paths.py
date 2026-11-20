"""Ordering rules over every path through the state machine, read from the state definitions."""

from collections.abc import Callable

import pytest

from isar.models.events import Event, Events
from isar.state_machine.state_machine import Edge, collect_edges
from isar.state_machine.states_enum import States
from tests.isar.state_machine.state_definitions.state_machine_driver import (
    StateMachineDriver,
)
from tests.isar.state_machine.state_definitions.test_state_behaviour import all_cases


def find_invalid_transition_path(
    edges: list[Edge],
    start: States,
    forbidden: Callable[[Edge], bool],
    satisfied_by: Callable[[Edge], bool],
) -> list[Edge] | None:
    """A path from start to a forbidden edge that never passes an edge satisfying the requirement."""
    frontier: list[tuple[States, list[Edge]]] = [(start, [])]
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


def describe(path: list[Edge]) -> str:
    return " -> ".join(f"{e.source.name} [{e.trigger.name}]" for e in path)


def test_behaviour_cases_cover_every_branch(
    events: Events, state_machine_driver: StateMachineDriver
) -> None:
    observed = set()
    for case in all_cases(events):
        state_machine_driver.enter(case.start, case.param)
        target = state_machine_driver.send(case.event, case.expect.message)
        observed.add((case.start.name, case.event.name, target))
    # Timer branches are not driven by an event, so they are tested separately
    declared = {
        (e.source, e.trigger.name, e.target)
        for e in collect_edges(events)
        if isinstance(e.trigger, Event)
    }
    assert declared <= observed, sorted(declared - observed)


def test_mission_result_is_reported_before_a_new_mission_starts(
    events: Events,
) -> None:
    result_publishers = (
        events.mqtt_queue.publish_mission_result,
        events.mqtt_queue.publish_mission_aborted,
    )
    path = find_invalid_transition_path(
        collect_edges(events),
        start=States.Monitor,
        forbidden=lambda e: e.trigger is events.api_requests.start_mission.request,
        satisfied_by=lambda e: any(effect in result_publishers for effect in e.effects),
    )
    if path is not None:
        pytest.fail(describe(path))
