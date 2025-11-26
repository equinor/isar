from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine


def test_transition_from_pausing_return_home_to_return_home_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.pausing_return_home_state.name  # type: ignore

    pausing_return_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_return_home_state.get_event_handler_by_name("successful_pause_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_mission_paused  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.return_home_paused_state.name  # type: ignore
