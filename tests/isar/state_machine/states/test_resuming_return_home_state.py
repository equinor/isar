from typing import cast

from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused


def test_transition_from_return_home_paused_to_resuming_return_home(
    events: Events,
) -> None:
    current_state = ReturnHomePaused(events)

    return_home_paused_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        return_home_paused_state.get_event_handler_by_name("resume_return_home_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is ResumingReturnHome
