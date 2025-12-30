from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.stopping_paused_return_home import (
    StoppingPausedReturnHome,
)
from robot_interface.models.mission.mission import Mission


def test_transition_from_pausing_return_home_to_return_home_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = PausingReturnHome(sync_state_machine)

    pausing_return_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        pausing_return_home_state.get_event_handler_by_name("successful_pause_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is ReturnHomePaused


def test_resuming_paused_return_home(
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


def test_transition_from_paused_return_home_to_stopping_paused_return_home_mission(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    sync_state_machine.current_state = ReturnHomePaused(sync_state_machine)

    return_home_paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        return_home_paused_state.get_event_handler_by_name("start_mission_event")
    )

    assert event_handler is not None

    example_mission: Mission = Mission(name="Dummy misson", tasks=[])

    transition = event_handler.handler(example_mission)

    sync_state_machine.current_state = transition(sync_state_machine)

    assert sync_state_machine.events.api_requests.start_mission.response.has_event()
    assert type(sync_state_machine.current_state) is StoppingPausedReturnHome


def test_stop_request_with_wrong_id_in_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Paused(sync_state_machine, "mission_id")

    paused_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        paused_state.get_event_handler_by_name("stop_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler("wrong_test_id")

    assert transition is None
    assert sync_state_machine.events.api_requests.stop_mission.response.has_event()
