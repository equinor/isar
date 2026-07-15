from typing import cast

from isar.models.events import EmptyMessage
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.pausing import Pausing


def test_transition_from_monitor_to_pausing(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Monitor(sync_state_machine.events, "mission_id")

    monitor_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = monitor_state.get_event_handler_by_name(
        "pause_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Pausing
