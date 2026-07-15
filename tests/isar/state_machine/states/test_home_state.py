from typing import cast

from isar.models.events import EmptyMessage
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.returning_home import ReturningHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import RobotStatus


def test_lockdown_transitions_to_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Lockdown(sync_state_machine.events)

    lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        lockdown_state.get_event_handler_by_name("release_from_lockdown")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    assert sync_state_machine.events.api_requests.release_from_lockdown.response.check()
    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Home


def test_state_machine_with_return_home_failure_successful_retries(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = ReturningHome(sync_state_machine.events)

    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler_success: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name("mission_succeeded_event")
    )
    event_handler_failure: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name("mission_failed_event")
    )

    assert event_handler_success is not None
    assert event_handler_failure is not None

    transition = event_handler_failure.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    assert transition is not None  # type: ignore
    assert type(sync_state_machine.current_state) is ReturningHome

    transition = event_handler_success.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Home


def test_intervention_needed_transitions_to_home_if_robot_is_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = InterventionNeeded(sync_state_machine.events)

    intervention_needed_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    transition = event_handler.handler(RobotStatus.Home)

    assert transition is not None

    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Home


def test_recharging_goes_to_home_when_battery_high(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Recharging(sync_state_machine.events)

    recharging_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        recharging_state.get_event_handler_by_name(
            "robot_battery_above_recharge_threshold_event"
        )
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine.events)

    assert type(sync_state_machine.current_state) is Home
