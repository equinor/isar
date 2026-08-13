from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states_enum import States


def test_monitor_goes_to_return_home_when_battery_low(events: Events) -> None:
    current_state = Monitor(events, "mission_id")
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.battery_below_mission_threshold
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.StoppingGoToRecharge
