from typing import cast

from isar.models.events import EmptyMessage
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.pausing import Pausing
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge
from isar.state_machine.states.stopping_paused_mission import StoppingPausedMission


def test_transition_from_pausing_to_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Pausing(sync_state_machine.events, "mission_id")

    pausing_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = pausing_state.get_event_handler_by_name(
        "successful_pause_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Paused


def test_transition_from_paused_to_stopping_paused_mission(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Paused(sync_state_machine.events, "test_id")

    paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = paused_state.get_event_handler_by_name(
        "stop_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler("test_id")

    sync_state_machine.current_state = transition(sync_state_machine.events)

    assert type(sync_state_machine.current_state) is StoppingPausedMission
    assert sync_state_machine.events.api_requests.stop_mission.response.has_event()


def test_transition_from_paused_to_stopping_to_recharge(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Paused(sync_state_machine.events, "test_id")

    paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = paused_state.get_event_handler_by_name(
        "robot_battery_below_threshold_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine.events)

    assert type(sync_state_machine.current_state) is StoppingGoToRecharge
    assert not sync_state_machine.events.api_requests.stop_mission.response.has_event()
    assert sync_state_machine.events.state_machine_events.stop_mission.has_event()


def test_stop_request_with_wrong_id_in_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Paused(sync_state_machine.events, "test_id")

    paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = paused_state.get_event_handler_by_name(
        "stop_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler("wrong_test_id")

    assert transition is None
    assert sync_state_machine.events.api_requests.stop_mission.response.has_event()
