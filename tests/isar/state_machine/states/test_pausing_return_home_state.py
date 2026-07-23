from typing import cast

from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.returning_home import ReturningHome


def test_transition_from_returning_home_to_pausing_return_home(events: Events) -> None:
    current_state = ReturningHome(events)

    returning_home_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        returning_home_state.get_event_handler_by_name("pause_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is PausingReturnHome
