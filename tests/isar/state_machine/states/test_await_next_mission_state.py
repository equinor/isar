from collections import deque

import pytest
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state import EventHandlerMapping, TimeoutHandlerMapping
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.resuming import Resuming
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)
from tests.test_mocks.task import StubTask
from tests.wait import wait_until


@pytest.mark.parametrize(
    "updates, expected_elapsed",
    [
        ([], 11),
        ([(2, 20)], 23),
        ([(2, 2)], 5),
        ([(2, 20), (4, 1)], 6),
        ([(2, 1), (3, 20)], 24),
    ],
)
def test_set_return_home_timeout(
    events: Events,
    mocker: MockerFixture,
    updates: list[tuple[int, int]],
    expected_elapsed: int,
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 10)
    clock = mocker.patch("isar.state_machine.state.time.monotonic", return_value=100)
    api_event = events.api_requests.set_return_home_timeout
    response = mocker.spy(api_event, "trigger_response")
    current_state = AwaitNextMission(events)
    other_timer = mocker.Mock(return_value=None)
    current_state.timers.append(
        TimeoutHandlerMapping("other_timer", 3, lambda: other_timer(clock()))
    )

    def advance_time(_: float) -> None:
        clock.return_value += 1
        elapsed = clock.return_value - 100
        assert elapsed <= expected_elapsed
        for at_second, seconds in updates:
            if elapsed == at_second:
                api_event.trigger_request(seconds)

    mocker.patch("isar.state_machine.state.time.sleep", side_effect=advance_time)

    transition = current_state.run()

    assert transition is not None
    assert transition(events).name is States.ReturningHome
    assert isinstance(
        events.action_requests.return_home.request.consume_event(),
        EmptyMessage,
    )
    assert clock.return_value == 100 + expected_elapsed
    assert response.call_count == len(updates)
    other_timer.assert_called_once_with(104)
    assert (
        current_state.get_event_timer_by_name(
            "should_return_home_timer"
        ).timeout_in_seconds
        == 10
    )
    assert (
        AwaitNextMission(events)
        .get_event_timer_by_name("should_return_home_timer")
        .timeout_in_seconds
        == 10
    )


def test_low_battery_overrides_updated_timeout(
    events: Events, mocker: MockerFixture
) -> None:
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 10)
    clock = mocker.patch("isar.state_machine.state.time.monotonic", return_value=100)
    api_event = events.api_requests.set_return_home_timeout
    response = mocker.spy(api_event, "trigger_response")
    api_event.trigger_request(60)

    def advance_time(_: float) -> None:
        clock.return_value += 1
        assert clock.return_value == 101
        events.robot_async_events.battery_below_mission_threshold.trigger_event(
            EmptyMessage()
        )
        api_event.trigger_request(120)

    mocker.patch("isar.state_machine.state.time.sleep", side_effect=advance_time)

    transition = AwaitNextMission(events).run()

    assert transition is not None
    assert transition(events).name is States.GoingToRecharging
    assert isinstance(
        events.action_requests.return_home.request.consume_event(),
        EmptyMessage,
    )
    response.assert_called_once()


def test_state_machine_with_successful_mission_stop(
    scheduling_utilities: SchedulingUtilities,
    robot_service_thread: RobotServiceThreadMock,
    state_machine_thread: StateMachineThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )

    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "ROBOT_API_STATUS_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 15)

    mission: Mission = Mission(
        id="id",
        name="Dummy misson",
        tasks=[StubTask.take_image() for _ in range(20)],
    )

    state_machine_thread.start()
    robot_service_thread.start()
    wait_until(
        lambda: States.Home in state_machine_thread.state_machine.transitions_list
    )
    scheduling_utilities.start_mission(mission=mission)
    wait_until(
        lambda: state_machine_thread.state_machine.current_state.name == States.Monitor
    )
    scheduling_utilities.stop_mission()

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.Stopping,
            States.AwaitNextMission,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )


def test_transition_from_resuming_to_paused(events: Events) -> None:
    current_state = Resuming(events, "mission_id")

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.action_requests.resume_mission.failure
    )

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
        )
    )

    current_state = transition(events)
    assert current_state.name is States.Paused


def test_unknown_status_transitions_to_await_next_mission_if_it_was_already_available(
    events: Events,
) -> None:
    current_state = UnknownStatus(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.robot_async_events.robot_status_update
    )

    transition = event_handler.handler(RobotStatus.Available)

    current_state = transition(events)
    assert current_state.name is States.AwaitNextMission


def test_transition_from_resuming_return_home_to_await_next_mission(
    events: Events,
) -> None:
    current_state = ResumingReturnHome(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.action_requests.resume_mission.failure
    )

    transition = event_handler.handler(
        ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
        )
    )

    current_state = transition(events)
    assert current_state.name is States.ReturnHomePaused
