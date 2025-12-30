from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.returning_home import ReturningHome
from robot_interface.models.mission.status import MissionStatus, RobotStatus


def test_lockdown_transitions_to_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.current_state = Lockdown(sync_state_machine)

    lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        lockdown_state.get_event_handler_by_name("release_from_lockdown")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.api_requests.release_from_lockdown.response.check()
    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Home


def test_state_machine_with_return_home_failure_successful_retries(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.current_state = ReturningHome(sync_state_machine)

    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("mission_status_event")
    )

    # We do not retry return home missions if the robot is not ready for another mission
    sync_state_machine.shared_state.robot_status.trigger_event(RobotStatus.Available)

    assert event_handler is not None

    transition = event_handler.handler(MissionStatus.Failed)

    assert transition is None  # type: ignore
    assert sync_state_machine.current_state.failed_return_home_attempts == 1

    transition = event_handler.handler(MissionStatus.Successful)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Home


def test_intervention_needed_transitions_to_home_if_robot_is_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = InterventionNeeded(sync_state_machine)

    intervention_needed_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        intervention_needed_state.get_event_handler_by_name("robot_status_event")
    )
    assert event_handler is not None

    sync_state_machine.shared_state.robot_status.trigger_event(RobotStatus.Home)

    transition = event_handler.handler(True)

    assert transition is not None

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Home


def test_recharging_goes_to_home_when_battery_high(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Recharging(sync_state_machine)

    recharging_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        recharging_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(99.9)

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is Home
