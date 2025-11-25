import time
from collections import deque
from http import HTTPStatus
from typing import Optional, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.modules import ApplicationContainer
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
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
    sync_state_machine.shared_state.mission_id.trigger_event("mission_id")
    sync_state_machine.state = sync_state_machine.stopping_go_to_recharge_state.name  # type: ignore
    stopping_go_to_recharge_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_go_to_recharge_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_recharge_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_stopping_failed  # type: ignore
    assert sync_state_machine.events.mqtt_queue.empty()

    transition()
    assert sync_state_machine.state is sync_state_machine.monitor_state.name  # type: ignore


def test_transitioning_to_monitor_from_stopping_when_return_home_cancelled(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    example_mission: Mission = Mission(
        name="Dummy return home misson", tasks=[ReturnToHome()]
    )
    sync_state_machine.events.api_requests.start_mission.request.trigger_event(
        example_mission
    )
    sync_state_machine.state = sync_state_machine.stopping_return_home_state.name  # type: ignore

    stopping_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )
    stopping_state.start()

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)
    transition()

    assert transition is sync_state_machine.start_mission_monitoring  # type: ignore
    assert sync_state_machine.state is sync_state_machine.monitor_state.name  # type: ignore


def test_stopping_lockdown_failing_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.stopping_go_to_lockdown_state.name  # type: ignore

    stopping_go_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_go_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_lockdown_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_stopping_failed  # type: ignore
    assert (
        not sync_state_machine.events.api_requests.send_to_lockdown.response.check().lockdown_started
    )

    assert sync_state_machine.events.mqtt_queue.empty()

    transition()
    assert sync_state_machine.state is sync_state_machine.monitor_state.name  # type: ignore


def test_transition_from_pausing_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.pausing_state.name  # type: ignore

    pausing_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_state.get_event_handler_by_name("failed_pause_event")
    )

    assert event_handler is not None

    error_event = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description=""
    )
    event_handler.event.trigger_event(error_event)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_pausing_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.monitor_state.name  # type: ignore


def test_transition_from_resuming_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.resuming_state.name  # type: ignore

    resuming_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.resuming_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        resuming_state.get_event_handler_by_name("successful_resume_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_resumed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.monitor_state.name  # type: ignore


def test_state_machine_with_unsuccessful_mission_stop(
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
