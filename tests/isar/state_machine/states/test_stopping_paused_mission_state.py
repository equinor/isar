from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason


def test_stopping_paused_mission_fails(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.mission_id.trigger_event("mission_id")
    sync_state_machine.state = sync_state_machine.stopping_paused_mission_state.name  # type: ignore
    stopping_paused_mission_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_paused_mission_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_paused_mission_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_stopping_failed  # type: ignore
    assert sync_state_machine.events.mqtt_queue.empty()

    transition()
    assert sync_state_machine.state is sync_state_machine.paused_state.name  # type: ignore


def test_stopping_paused_mission_succeeds(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    sync_state_machine.shared_state.mission_id.trigger_event("mission_id")
    sync_state_machine.state = sync_state_machine.stopping_paused_mission_state.name  # type: ignore
    stopping_paused_mission_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_paused_mission_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_paused_mission_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_stopped  # type: ignore
    assert sync_state_machine.events.mqtt_queue.empty()

    transition()
    assert sync_state_machine.state is sync_state_machine.await_next_mission_state.name  # type: ignore


def test_stopping_paused_mission_succeeds_with_low_battery(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.shared_state.mission_id.trigger_event("mission_id")
    sync_state_machine.state = sync_state_machine.stopping_paused_mission_state.name  # type: ignore
    stopping_paused_mission_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_paused_mission_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_paused_mission_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.start_return_home_monitoring  # type: ignore
    assert sync_state_machine.events.mqtt_queue.empty()

    transition()
    assert sync_state_machine.state is sync_state_machine.returning_home_state.name  # type: ignore
