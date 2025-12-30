from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.pausing import Pausing
from isar.state_machine.states.stopping_paused_mission import StoppingPausedMission


def test_transition_from_pausing_to_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Pausing(sync_state_machine, "mission_id")

    pausing_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        pausing_state.get_event_handler_by_name("successful_pause_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Paused


def test_transition_from_paused_to_stopping_paused_mission(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Paused(sync_state_machine, "test_id")

    paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        paused_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler("test_id")

    assert sync_state_machine.events.api_requests.stop_mission.response.has_event()

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is StoppingPausedMission


def test_stop_request_with_wrong_id_in_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Paused(sync_state_machine, "test_id")

    paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        paused_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler("wrong_test_id")

    assert transition is None
    assert sync_state_machine.events.api_requests.stop_mission.response.has_event()
