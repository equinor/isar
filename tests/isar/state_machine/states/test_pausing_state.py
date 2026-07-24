from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.pausing import Pausing


def test_transition_from_monitor_to_pausing(events: Events) -> None:
    current_state = Monitor(events, "mission_id")

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "pause_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Pausing
