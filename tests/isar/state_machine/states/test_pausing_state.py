from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine


def test_transition_from_monitor_to_pausing(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.monitor_state.name  # type: ignore

    monitor_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.monitor_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("pause_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.pause  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.pausing_state.name  # type: ignore
