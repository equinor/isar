from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine


def test_transition_from_pausing_to_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.pausing_state.name  # type: ignore

    pausing_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_state.get_event_handler_by_name("successful_pause_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_paused  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.paused_state.name  # type: ignore


def test_transition_from_paused_to_stopping_paused_mission(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.paused_state.name  # type: ignore
    sync_state_machine.shared_state.mission_id.trigger_event("test_id")

    paused_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.paused_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        paused_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event("test_id")
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.stop  # type: ignore
    assert sync_state_machine.events.api_requests.stop_mission.response.has_event()

    transition()

    assert sync_state_machine.state is sync_state_machine.stopping_paused_mission_state.name  # type: ignore


def test_stop_request_with_wrong_id_in_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.paused_state.name  # type: ignore
    sync_state_machine.shared_state.mission_id.trigger_event("test_id")

    paused_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.paused_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        paused_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event("wrong_test_id")
    transition = event_handler.handler(event_handler.event)

    assert transition is None
    assert sync_state_machine.events.api_requests.stop_mission.response.has_event()
