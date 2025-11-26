from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine


def test_return_home_cancelled_when_new_mission_received(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("start_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.stop_return_home  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.stopping_return_home_state.name  # type: ignore
