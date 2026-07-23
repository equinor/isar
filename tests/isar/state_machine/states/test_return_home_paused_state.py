from typing import cast

from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.stopping_paused_return_home import (
    StoppingPausedReturnHome,
)
from robot_interface.models.mission.mission import Mission


def test_transition_from_pausing_return_home_to_return_home_paused(
    events: Events,
) -> None:
    current_state = PausingReturnHome(events)

    pausing_return_home_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        pausing_return_home_state.get_event_handler_by_name("successful_pause_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is ReturnHomePaused


def test_resuming_paused_return_home(events: Events) -> None:
    current_state = ReturnHomePaused(events)

    return_home_paused_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        return_home_paused_state.get_event_handler_by_name("resume_return_home_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is ResumingReturnHome


def test_transition_from_paused_return_home_to_stopping_paused_return_home_mission(
    events: Events,
) -> None:
    current_state = ReturnHomePaused(events)

    return_home_paused_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = (
        return_home_paused_state.get_event_handler_by_name("start_mission_event")
    )

    assert event_handler is not None

    example_mission: Mission = Mission(name="Dummy misson", tasks=[])

    transition = event_handler.handler(example_mission)

    current_state = transition(events)

    assert events.api_requests.start_mission.response.has_event()
    assert type(current_state) is StoppingPausedReturnHome


def test_stop_request_with_wrong_id_in_paused(events: Events) -> None:
    current_state = Paused(events, "mission_id")

    paused_state: State = cast(State, current_state)
    event_handler: EventHandlerMapping | None = paused_state.get_event_handler_by_name(
        "stop_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler("wrong_test_id")

    assert transition is None
    assert events.api_requests.stop_mission.response.has_event()
