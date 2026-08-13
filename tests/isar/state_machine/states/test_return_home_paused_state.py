from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
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

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_successfully_paused
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is ReturnHomePaused


def test_resuming_paused_return_home(events: Events) -> None:
    current_state = ReturnHomePaused(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.resume_mission.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is ResumingReturnHome


def test_transition_from_paused_return_home_to_stopping_paused_return_home_mission(
    events: Events,
) -> None:
    current_state = ReturnHomePaused(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.start_mission.request
    )

    example_mission: Mission = Mission(id="id", name="Dummy misson", tasks=[])

    transition = event_handler.handler(example_mission)

    current_state = transition(events)

    assert events.api_requests.start_mission.response.has_event()
    assert type(current_state) is StoppingPausedReturnHome


def test_stop_request_with_wrong_id_in_paused(events: Events) -> None:
    current_state = Paused(events, "mission_id")

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.stop_mission.request
    )

    transition = event_handler.handler("wrong_test_id")

    assert transition is None
    assert events.api_requests.stop_mission.response.has_event()
