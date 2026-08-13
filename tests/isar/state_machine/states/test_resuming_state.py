from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.paused import Paused
from isar.state_machine.states_enum import States


def test_transition_from_paused_to_resuming(events: Events) -> None:
    current_state = Paused(events, "mission_id")

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.resume_mission.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.Resuming
