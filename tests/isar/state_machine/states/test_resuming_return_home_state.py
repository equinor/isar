from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states_enum import States


def test_transition_from_return_home_paused_to_resuming_return_home(
    events: Events,
) -> None:
    current_state = ReturnHomePaused(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.resume_mission.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.ResumingReturnHome
