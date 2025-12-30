from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.home import Home
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.recharging import Recharging
from robot_interface.models.mission.status import MissionStatus


def test_going_to_recharging_goes_to_recharge(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = GoingToRecharging(sync_state_machine)
    going_to_recharging_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        going_to_recharging_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(MissionStatus.Successful)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Recharging


def test_home_goes_to_recharging_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Home(sync_state_machine)
    home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = home_state.get_event_handler_by_name(
        "robot_battery_update_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(10.0)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Recharging


def test_lockdown_transitions_to_recharing_if_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = Lockdown(sync_state_machine)

    lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        lockdown_state.get_event_handler_by_name("release_from_lockdown")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.api_requests.release_from_lockdown.response.check()
    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Recharging


def test_recharging_continues_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Recharging(sync_state_machine)
    recharging_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        recharging_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(10.0)

    assert transition is None
