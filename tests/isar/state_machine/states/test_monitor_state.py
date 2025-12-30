import time
from collections import deque
from http import HTTPStatus
from typing import Optional, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.modules import ApplicationContainer
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
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
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import ReturnToHome
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


def test_stopping_to_recharge_goes_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = StoppingGoToRecharge(
        sync_state_machine, "mission_id"
    )
    stopping_go_to_recharge_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_recharge_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Monitor


def test_transitioning_to_monitor_from_stopping_when_return_home_cancelled(
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


def test_stopping_lockdown_failing_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.current_state = StoppingGoToLockdown(
        sync_state_machine, "mission_id"
    )

    stopping_go_to_lockdown_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_lockdown_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    assert (
        not sync_state_machine.events.api_requests.send_to_lockdown.response.check().lockdown_started
    )

    assert sync_state_machine.events.mqtt_queue.empty()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Monitor


def test_transition_from_pausing_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Pausing(sync_state_machine, "mission_id")

    pausing_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        pausing_state.get_event_handler_by_name("failed_pause_event")
    )

    assert event_handler is not None

    error_event = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
    )
    transition = event_handler.handler(error_event)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Monitor


def test_transition_from_resuming_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.current_state = Resuming(sync_state_machine, "mission_id")

    resuming_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        resuming_state.get_event_handler_by_name("successful_resume_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
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
