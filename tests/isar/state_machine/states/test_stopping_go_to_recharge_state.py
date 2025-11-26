from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine


def test_monitor_goes_to_return_home_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.monitor_state.name  # type: ignore
    monitor_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.monitor_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(10.0)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.stop_go_to_recharge  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.stopping_go_to_recharge_state.name  # type: ignore
