from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, TimeoutHandlerMapping
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.home import Home
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission, ReturnHomeMission


def test_transitioning_to_returning_home_from_stopping_when_return_home_failed(
    events: Events,
) -> None:
    example_mission: Mission = ReturnHomeMission()
    current_state = StoppingReturnHome(events, example_mission)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "successful_stop_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())
    current_state = transition(events)

    assert type(current_state) is Monitor


def test_transition_from_pausing_return_home_to_returning_home(events: Events) -> None:
    current_state = PausingReturnHome(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "failed_pause_event"
    )

    assert event_handler is not None

    error_event = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
    )
    transition = event_handler.handler(error_event)

    current_state = transition(events)
    assert type(current_state) is ReturningHome


def test_transition_from_resuming_return_home_to_returning_home_state(
    events: Events,
) -> None:
    current_state = ResumingReturnHome(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "successful_resume_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is ReturningHome


def test_transition_from_returning_home_to_home_robot_status_not_updated(
    events: Events,
) -> None:
    current_state: State = ReturningHome(events)

    event_handler: EventHandlerMapping | None = current_state.get_event_handler_by_name(
        "mission_succeeded_event"
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert type(current_state) is Home
    assert not events.robot_service_events.robot_status_update.check()

    event_handler_robot_status: EventHandlerMapping | None = (
        current_state.get_event_handler_by_name("robot_status_event")
    )

    assert event_handler_robot_status is not None

    assert not event_handler_robot_status.event.has_event()


def test_return_home_starts_when_battery_is_low(events: Events) -> None:
    current_state = AwaitNextMission(events)

    timer: TimeoutHandlerMapping | None = current_state.get_event_timer_by_name(
        "should_return_home_timer"
    )

    assert timer is not None

    transition = timer.handler()

    current_state = transition(events)

    assert type(current_state) is ReturningHome
