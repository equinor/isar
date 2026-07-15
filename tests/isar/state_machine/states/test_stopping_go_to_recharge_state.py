from typing import cast

from isar.eventhandlers.state import EventHandlerMapping, State
from isar.models.events import EmptyMessage
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge


def test_monitor_goes_to_return_home_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Monitor(sync_state_machine, "mission_id")
    monitor_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = monitor_state.get_event_handler_by_name(
        "robot_battery_below_threshold_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is StoppingGoToRecharge
