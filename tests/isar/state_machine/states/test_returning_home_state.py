from typing import Optional, cast

from isar.eventhandlers.eventhandler import (
    EventHandlerMapping,
    State,
    TimeoutHandlerMapping,
)
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.home import Home
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import ReturnToHome


def test_transitioning_to_returning_home_from_stopping_when_return_home_failed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    example_mission: Mission = Mission(
        name="Dummy return home misson", tasks=[ReturnToHome()]
    )
    sync_state_machine.current_state = StoppingReturnHome(
        sync_state_machine, example_mission
    )

    stopping_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)
    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is Monitor


def test_transition_from_pausing_return_home_to_returning_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = PausingReturnHome(sync_state_machine)

    pausing_return_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        pausing_return_home_state.get_event_handler_by_name("failed_pause_event")
    )

    assert event_handler is not None

    error_event = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
    )
    transition = event_handler.handler(error_event)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is ReturningHome


def test_transition_from_resuming_return_home_to_returning_home_state(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = ResumingReturnHome(sync_state_machine)

    resuming_return_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        resuming_return_home_state.get_event_handler_by_name("successful_resume_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is ReturningHome


def test_transition_from_returning_home_to_home_robot_status_not_updated(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    sync_state_machine.current_state = ReturningHome(sync_state_machine)

    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("mission_status_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(MissionStatus.Successful)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Home
    assert (
        not sync_state_machine.events.robot_service_events.robot_status_changed.check()
    )

    home_state: State = cast(State, sync_state_machine.current_state)
    event_handler_robot_status: Optional[EventHandlerMapping] = (
        home_state.get_event_handler_by_name("robot_status_event")
    )

    assert event_handler_robot_status is not None

    assert not event_handler_robot_status.event.has_event()


def test_return_home_not_cancelled_when_battery_is_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    events = sync_state_machine.events
    sync_state_machine.current_state = ReturningHome(sync_state_machine)

    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("start_mission_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert transition is None
    assert events.api_requests.start_mission.response.has_event()
    start_mission_event_response = events.api_requests.start_mission.response.check()
    assert not start_mission_event_response.mission_started


def test_return_home_starts_when_battery_is_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = AwaitNextMission(sync_state_machine)

    await_next_mission_state: State = cast(State, sync_state_machine.current_state)
    timer: Optional[TimeoutHandlerMapping] = (
        await_next_mission_state.get_event_timer_by_name("should_return_home_timer")
    )

    assert timer is not None

    transition = timer.handler()

    sync_state_machine.current_state = transition(sync_state_machine)

    assert type(sync_state_machine.current_state) is ReturningHome
