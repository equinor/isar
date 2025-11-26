from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine
from robot_interface.models.mission.status import MissionStatus


def test_mission_stopped_when_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.monitor_state.name  # type: ignore

    monitor_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.monitor_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.stop_go_to_lockdown  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.stopping_go_to_lockdown_state.name  # type: ignore


def test_going_to_lockdown_transitions_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.going_to_lockdown_state.name  # type: ignore

    going_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(MissionStatus.Successful)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.reached_lockdown  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.lockdown_state.name  # type: ignore
