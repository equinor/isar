import time
from collections import deque
from http import HTTPStatus
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.models.events import EmptyMessage
from isar.modules import ApplicationContainer
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.pausing import Pausing
from isar.state_machine.states.resuming import Resuming
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotException,
)
from robot_interface.models.mission.mission import Mission, ReturnHomeMission
from robot_interface.models.mission.status import MissionStatus
from tests.test_mocks.robot_interface import (
    StubRobot,
    StubRobotMissionStatusRaisesException,
)
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)
from tests.test_mocks.task import StubTask


def _mock_robot_exception_with_message() -> RobotException:
    raise RobotException(
        error_reason=ErrorReason.RobotUnknownErrorException,
        error_description="This is an example error description",
    )


def test_stopping_to_recharge_goes_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = StoppingGoToRecharge(sync_state_machine.events)
    stopping_go_to_recharge_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_go_to_recharge_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine.events)

    assert not sync_state_machine.events.mqtt_queue.empty()
    assert type(sync_state_machine.current_state) is InterventionNeeded


def test_transitioning_to_monitor_from_stopping_when_return_home_cancelled(
    sync_state_machine: StateMachine,
) -> None:
    example_mission: Mission = ReturnHomeMission()
    sync_state_machine.current_state = StoppingReturnHome(
        sync_state_machine.events, example_mission
    )

    stopping_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())
    sync_state_machine.current_state = transition(sync_state_machine.events)

    assert type(sync_state_machine.current_state) is Monitor


def test_stopping_lockdown_failing_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = StoppingGoToLockdown(
        sync_state_machine.events, "mission_id"
    )

    stopping_go_to_lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        stopping_go_to_lockdown_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    assert (
        not sync_state_machine.events.api_requests.send_to_lockdown.response.check().lockdown_started
    )

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Monitor


def test_transition_from_pausing_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Pausing(sync_state_machine.events, "mission_id")

    pausing_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = pausing_state.get_event_handler_by_name(
        "failed_pause_event"
    )

    assert event_handler is not None

    error_event = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
    )
    transition = event_handler.handler(error_event)

    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Monitor


def test_transition_from_resuming_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Resuming(sync_state_machine.events, "mission_id")

    resuming_state: State = cast(State, sync_state_machine.current_state)
    event_handler: EventHandlerMapping | None = (
        resuming_state.get_event_handler_by_name("successful_resume_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(EmptyMessage())

    sync_state_machine.current_state = transition(sync_state_machine.events)
    assert type(sync_state_machine.current_state) is Monitor


def test_state_machine_with_unsuccessful_mission_stop(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )
    mocker.patch.object(
        StubRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.5)
    scheduling_utilities.stop_mission()
    time.sleep(2)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.Stopping,
            States.Monitor,
        ]
    )


def test_state_machine_with_unsuccessful_mission_stop_with_mission_id(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)

    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )
    mocker.patch.object(
        StubRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    settings.FSM_SLEEP_TIME = 0

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)
    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.stop_mission(str(uuid4()))

    assert exception_details.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE.value
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
        ]
    )


def test_robot_mission_status_exception_handling(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker: MockerFixture,
) -> None:
    mission = Mission(
        name="Dummy mission",
        tasks=[StubTask.take_image()],
    )
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    robot_service_thread.robot_service.robot = StubRobotMissionStatusRaisesException()

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.start_mission(mission=mission)

    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
        ]
    )


def test_transition_from_monitor_to_stopping_to_recharge(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Monitor(sync_state_machine.events, "test_id")

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
