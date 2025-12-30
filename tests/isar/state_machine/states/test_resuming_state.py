from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.resuming import Resuming


def test_transition_from_paused_to_resuming(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Paused(sync_state_machine, "mission_id")

    paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        paused_state.get_event_handler_by_name("resume_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Resuming
