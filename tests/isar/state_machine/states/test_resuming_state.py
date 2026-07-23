from typing import cast

from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.resuming import Resuming


def test_transition_from_paused_to_resuming(events: Events) -> None:
    current_state = Paused(events, "mission_id")

    paused_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = paused_state.get_event_handler_by_name(
        "resume_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Resuming
