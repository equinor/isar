from typing import cast

from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge


def test_monitor_goes_to_return_home_when_battery_low(events: Events) -> None:
    current_state = Monitor(events, "mission_id")
    monitor_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = monitor_state.get_event_handler_by_name(
        "robot_battery_below_threshold_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is StoppingGoToRecharge
