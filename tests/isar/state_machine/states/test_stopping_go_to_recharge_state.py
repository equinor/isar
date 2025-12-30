from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge


def test_monitor_goes_to_return_home_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Monitor(sync_state_machine, "mission_id")
    monitor_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(10.0)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is StoppingGoToRecharge
