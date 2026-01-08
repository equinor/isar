from typing import Optional, cast

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.models.events import EmptyMessage
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.returning_home import ReturningHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import RobotStatus


def test_going_to_recharging_goes_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = GoingToRecharging(sync_state_machine)
    going_to_recharging_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        going_to_recharging_state.get_event_handler_by_name("mission_failed_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is InterventionNeeded


def test_going_to_lockdown_task_failed_transitions_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = GoingToLockdown(sync_state_machine)

    going_to_lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_failed_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is InterventionNeeded


def test_going_to_lockdown_mission_failed_transitions_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = GoingToLockdown(sync_state_machine)

    going_to_lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_failed_event")
    )

    assert event_handler is not None

    # The type of error reason is not important for this test
    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is InterventionNeeded


def test_state_machine_with_return_home_failure(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.current_state = ReturningHome(sync_state_machine)

    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("mission_failed_event")
    )

    # We do not retry return home missions if the robot is not ready for another mission
    sync_state_machine.shared_state.robot_status.trigger_event(RobotStatus.Available)

    assert event_handler is not None

    for i in range(settings.RETURN_HOME_RETRY_LIMIT - 1):

        transition = event_handler.handler(
            ErrorMessage(
                error_reason=ErrorReason.RobotUnknownErrorException,
                error_description="test",
            )
        )

        assert transition is None  # type: ignore
        assert sync_state_machine.current_state.failed_return_home_attempts == i + 1

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        )
    )

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is InterventionNeeded


def test_intervention_needed_transitions_does_not_transition_if_status_is_not_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = InterventionNeeded(sync_state_machine)

    intervention_needed_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    statuses = [
        RobotStatus.Available,
        RobotStatus.BlockedProtectiveStop,
        RobotStatus.Busy,
        RobotStatus.Paused,
        RobotStatus.Offline,
    ]
    for status in statuses:
        sync_state_machine.shared_state.robot_status.update(status)

        transition = event_handler.handler(EmptyMessage())

        assert transition is None  # type: ignore
