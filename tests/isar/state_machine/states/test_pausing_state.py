from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states_enum import States


def test_transition_from_monitor_to_pausing(events: Events) -> None:
    current_state = State(Monitor(events, "mission_id"))

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.pause_mission.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = State(transition(events))
    assert current_state.name is States.Pausing
