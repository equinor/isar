from typing import Optional, cast

from isar.eventhandlers.eventhandler import (
    EventHandlerBase,
    EventHandlerMapping,
    TimeoutHandlerMapping,
)
from isar.state_machine.state_machine import StateMachine
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus, RobotStatus


def test_transitioning_to_returning_home_from_stopping_when_return_home_failed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.state = sync_state_machine.stopping_return_home_state.name  # type: ignore

    stopping_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)
    transition()

    assert transition is sync_state_machine.start_return_home_monitoring  # type: ignore
    assert sync_state_machine.state is sync_state_machine.returning_home_state.name  # type: ignore


def test_transition_from_pausing_return_home_to_returning_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.pausing_return_home_state.name  # type: ignore

    pausing_return_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_return_home_state.get_event_handler_by_name("failed_pause_event")
    )

    assert event_handler is not None

    error_event = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
    )
    event_handler.event.trigger_event(error_event)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_mission_pausing_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.returning_home_state.name  # type: ignore


def test_transition_from_resuming_return_home_to_returning_home_state(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.resuming_return_home_state.name  # type: ignore

    resuming_return_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.resuming_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        resuming_return_home_state.get_event_handler_by_name("successful_resume_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_mission_resumed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.returning_home_state.name  # type: ignore


def test_transition_from_returning_home_to_home_robot_status_not_updated(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    sync_state_machine.shared_state.mission_id.trigger_event("mission_id")
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(MissionStatus.Successful)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.returned_home  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.home_state.name  # type: ignore
    assert (
        not sync_state_machine.events.robot_service_events.robot_status_changed.check()
    )

    home_state: EventHandlerBase = cast(EventHandlerBase, sync_state_machine.home_state)
    event_handler_robot_status: Optional[EventHandlerMapping] = (
        home_state.get_event_handler_by_name("robot_status_event")
    )

    assert event_handler_robot_status is not None

    # This status should not be used, if the event handler is working correctly
    sync_state_machine.shared_state.robot_status.trigger_event(RobotStatus.Busy)

    transition = event_handler_robot_status.handler(event_handler_robot_status.event)

    assert transition is None


def test_return_home_not_cancelled_when_battery_is_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    events = sync_state_machine.events

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("start_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is None
    assert events.api_requests.start_mission.response.has_event()
    start_mission_event_response = events.api_requests.start_mission.response.check()
    assert not start_mission_event_response.mission_started


def test_return_home_starts_when_battery_is_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    await_next_mission_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.await_next_mission_state
    )
    timer: Optional[TimeoutHandlerMapping] = (
        await_next_mission_state.get_event_timer_by_name("should_return_home_timer")
    )

    assert timer is not None

    transition = timer.handler()

    assert transition is sync_state_machine.start_return_home_monitoring  # type: ignore
