"""Ordering rules over every path through the state machine, read from the state definitions."""

from collections.abc import Callable

import pytest

from isar.models.events import Event, Events, RobotActionEvent
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
            if edge.source != state:
                continue
            if forbidden(edge):
                return [*path, edge]
            if satisfied_by(edge):
                continue
            if edge.target not in seen:
                seen.add(edge.target)
                frontier.append((edge.target, [*path, edge]))
    return None


def describe(path: list[Edge]) -> str:
    return " -> ".join(f"{e.source.name} [{e.trigger.name}]" for e in path)


def test_forbidden_trigger_takes_precedence_over_effect(events: Events) -> None:
    request = events.api_requests.set_maintenance_mode.request
    response = events.api_requests.set_maintenance_mode.trigger_response
    edge = next(
        edge
        for edge in collect_edges(events)
        if edge.trigger is request and response in edge.effects
    )

    path = find_invalid_transition_path(
        [edge],
        start=edge.source,
        forbidden=lambda e: e.trigger is request,
        satisfied_by=lambda e: response in e.effects,
    )
    assert path == [edge]


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


def test_maintenance_api_response_is_sent_after_the_request(
    events: Events,
) -> None:
    edges = collect_edges(events)
    request = events.api_requests.set_maintenance_mode.request
    response = events.api_requests.set_maintenance_mode.trigger_response

    for request_edge in edges:
        if request_edge.trigger is not request or response in request_edge.effects:
            continue

        path = find_invalid_transition_path(
            edges,
            start=request_edge.target,
            forbidden=lambda e: e.trigger is request,
            satisfied_by=lambda e: response in e.effects,
        )
        if path is not None:
            pytest.fail(describe([request_edge, *path]))


def test_send_to_lockdown_api_response_is_sent_after_the_request(
    events: Events,
) -> None:
    edges = collect_edges(events)
    request = events.api_requests.send_to_lockdown.request
    response = events.api_requests.send_to_lockdown.trigger_response

    for request_edge in edges:
        if request_edge.trigger is not request or response in request_edge.effects:
            continue

        path = find_invalid_transition_path(
            edges,
            start=request_edge.target,
            forbidden=lambda e: e.trigger is request,
            satisfied_by=lambda e: response in e.effects,
        )
        if path is not None:
            pytest.fail(describe([request_edge, *path]))


def test_every_robot_action_request_target_handles_outcomes(
    events: Events,
) -> None:
    edges = collect_edges(events)
    actions = {
        name: action
        for name, action in vars(events.action_requests).items()
        if isinstance(action, RobotActionEvent)
    }
    # Resuming a paused return-home into GoingToLockdown intentionally stays in
    # GoingToLockdown on resume_mission.success and waits for return_home outcomes.
    allowed_ignored_success = {("resume_mission", States.GoingToLockdown)}

    missing: list[str] = []
    for name, action in actions.items():
        targets = {
            edge.target for edge in edges if action.trigger_request in edge.effects
        }
        assert targets, f"No state transition requests action_requests.{name}"
        for target in sorted(targets, key=lambda state: state.name):
            handled_triggers = {edge.trigger for edge in edges if edge.source == target}
            if action.failure not in handled_triggers:
                missing.append(f"{target.name} does not handle {action.failure.name}")
            if (
                action.success not in handled_triggers
                and (name, target) not in allowed_ignored_success
            ):
                missing.append(f"{target.name} does not handle {action.success.name}")

    assert not missing, "\n".join(missing)
