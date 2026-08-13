from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.stopping_paused_return_home import (
    StoppingPausedReturnHome,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from tests.test_mocks.task import StubTask


def test_transition_to_stopping_paused_return_home_replies_to_API(
    events: Events,
) -> None:
    mission: Mission = Mission(
        id="id", name="Dummy misson", tasks=[StubTask.take_image()]
    )
    current_state = ReturnHomePaused(events)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.start_mission.request
    )

    transition = event_handler.handler(mission)

    current_state = transition(events)
    assert current_state.name is States.StoppingPausedReturnHome
    assert events.api_requests.start_mission.response.has_event()


def test_stopping_paused_return_home_mission_fails(events: Events) -> None:
    mission: Mission = Mission(
        id="id", name="Dummy misson", tasks=[StubTask.take_image()]
    )
    current_state = StoppingPausedReturnHome(events, mission)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_failed_to_stop
    )

    transition = event_handler.handler(EmptyMessage())

    assert not events.api_requests.start_mission.response.has_event()

    current_state = transition(events)
    assert current_state.name is States.ReturnHomePaused


def test_stopping_paused_return_home_mission_succeeds(events: Events) -> None:
    mission: Mission = Mission(
        id="id", name="Dummy misson", tasks=[StubTask.take_image()]
    )
    current_state = StoppingPausedReturnHome(events, mission)
    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_service_events.mission_successfully_stopped
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.Monitor
