from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused


def test_transition_from_return_home_paused_to_resuming_return_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = ReturnHomePaused(sync_state_machine)

    return_home_paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        return_home_paused_state.get_event_handler_by_name("resume_return_home_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is ResumingReturnHome
