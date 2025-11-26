from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine
from robot_interface.models.mission.status import MissionStatus


def test_going_to_recharging_goes_to_recharge(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.going_to_recharging_state.name  # type: ignore
    going_to_recharging_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_recharging_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_recharging_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(MissionStatus.Successful)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.starting_recharging  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.recharging_state.name  # type: ignore


def test_home_goes_to_recharging_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.home_state.name  # type: ignore
    home_state: EventHandlerBase = cast(EventHandlerBase, sync_state_machine.home_state)
    event_handler: Optional[EventHandlerMapping] = home_state.get_event_handler_by_name(
        "robot_battery_update_event"
    )

    assert event_handler is not None

    event_handler.event.trigger_event(10.0)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.starting_recharging  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.recharging_state.name  # type: ignore


def test_lockdown_transitions_to_recharing_if_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.lockdown_state.name  # type: ignore

    lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        lockdown_state.get_event_handler_by_name("release_from_lockdown")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.starting_recharging  # type: ignore
    assert sync_state_machine.events.api_requests.release_from_lockdown.response.check()
    transition()
    assert sync_state_machine.state is sync_state_machine.recharging_state.name  # type: ignore


def test_recharging_continues_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    recharging_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.recharging_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        recharging_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(10.0)
    transition = event_handler.handler(event_handler.event)

    assert transition is None
