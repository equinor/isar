from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from tests.test_mocks.task import StubTask


def test_return_home_cancelled_when_new_mission_received(events: Events) -> None:
    current_state = ReturningHome(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "start_mission_event"
    )

    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])

    assert event_handler is not None

    transition = event_handler.handler(mission)

    current_state = transition(events)
    assert type(current_state) is StoppingReturnHome


def test_transition_to_stopping_return_home_replies_to_API(events: Events) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    current_state = ReturningHome(events)
    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "start_mission_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(mission)

    current_state = transition(events)
    assert type(current_state) is StoppingReturnHome
    assert events.api_requests.start_mission.response.has_event()


def test_stopping_return_home_mission_fails(events: Events) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    current_state = StoppingReturnHome(events, mission)
    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "failed_stop_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    assert not events.api_requests.start_mission.response.has_event()

    current_state = transition(events)
    assert type(current_state) is ReturningHome


def test_stopping_return_home_mission_succeeds(events: Events) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    current_state = StoppingReturnHome(events, mission)
    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "successful_stop_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Monitor
