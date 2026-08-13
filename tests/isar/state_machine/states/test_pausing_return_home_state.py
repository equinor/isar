from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.returning_home import ReturningHome


def test_transition_from_returning_home_to_pausing_return_home(events: Events) -> None:
    current_state = ReturningHome(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.pause_mission.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is PausingReturnHome
