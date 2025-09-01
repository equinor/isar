import time
from collections import deque
from http import HTTPStatus
from threading import Thread
from typing import List, Optional, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import (
    EventHandlerBase,
    EventHandlerMapping,
    TimeoutHandlerMapping,
)
from isar.modules import ApplicationContainer
from isar.robot.robot import Robot
from isar.robot.robot_status import RobotStatusThread
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine, main
from isar.state_machine.states_enum import States
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorReason,
    RobotException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_double.pose import DummyPose
from tests.test_double.robot_interface import (
    StubRobot,
    StubRobotBlockedProtectiveStopToRobotStandingStillTest,
    StubRobotHomeToRobotStandingStillTest,
    StubRobotOfflineToHomeTest,
    StubRobotOfflineToRobotStandingStillTest,
)
from tests.test_double.task import StubTask


class StateMachineThreadMock(object):
    def __init__(self, container: ApplicationContainer) -> None:
        self.state_machine: StateMachine = container.state_machine()
        self._thread: Thread = Thread(target=main, args=[self.state_machine])

    def start(self):
        self._thread.start()

    def join(self):
        self.state_machine.terminate()
        self._thread.join()


class UploaderThreadMock(object):
    def __init__(self, container: ApplicationContainer) -> None:
        self.uploader: Uploader = container.uploader()
        self._thread: Thread = Thread(target=self.uploader.run)

    def start(self):
        self._thread.start()

    def join(self):
        self.uploader.stop()
        self._thread.join()


class RobotServiceThreadMock(object):
    def __init__(self, robot_service: Robot) -> None:
        self.robot_service: Robot = robot_service

    def start(self) -> None:
        self._thread: Thread = Thread(target=self.robot_service.run)
        self._thread.start()

    def join(self):
        self.robot_service.stop()
        self._thread.join()


def test_initial_unknown_status(state_machine) -> None:
    assert state_machine.state == "unknown_status"


def test_reset_state_machine(state_machine) -> None:
    state_machine.reset_state_machine()

    assert state_machine.current_task is None
    assert state_machine.current_mission is None


def test_state_machine_transitions_when_running_full_mission(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01
    state_machine_thread.start()
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    robot_service_thread.start()
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow enough time to run mission and return home

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_battery_too_low_to_start_mission(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01
    state_machine_thread.start()
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(StubRobot, "get_battery_level", return_value=10.0)
    robot_service_thread.start()
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.start_mission(mission=mission)
        assert exception_details.value.status_code == 408

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
        ]
    )


def test_return_home_not_cancelled_when_battery_is_low(
    container: ApplicationContainer,
) -> None:
    state_machine: StateMachine = container.state_machine()
    state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    events = state_machine.events

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("start_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is None
    assert events.api_requests.start_mission.response.has_event()
    start_mission_event_response = events.api_requests.start_mission.response.check()
    assert not start_mission_event_response.mission_started


def test_return_home_starts_when_battery_is_low(
    container: ApplicationContainer,
) -> None:
    state_machine: StateMachine = container.state_machine()
    state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    await_next_mission_state: EventHandlerBase = cast(
        EventHandlerBase, state_machine.await_next_mission_state
    )
    timer: Optional[TimeoutHandlerMapping] = (
        await_next_mission_state.get_event_timer_by_name("should_return_home_timer")
    )

    assert timer is not None

    transition = timer.handler()

    assert transition is state_machine.request_return_home  # type: ignore


def test_monitor_goes_to_return_home_when_battery_low(
    container: ApplicationContainer,
) -> None:
    state_machine: StateMachine = container.state_machine()

    state_machine.mission_ongoing = True

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    state_machine.current_task = task_1

    monitor_state: EventHandlerBase = cast(
        EventHandlerBase, state_machine.monitor_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(10.0, timeout=1)
    transition = event_handler.handler(event_handler.event)

    assert transition is state_machine.request_return_home  # type: ignore
    assert not state_machine.events.mqtt_queue.empty()

    mqtt_message = state_machine.events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED
    assert state_machine.events.mqtt_queue.get()[0]


def test_return_home_goes_to_recharging_when_battery_low(
    container: ApplicationContainer,
) -> None:
    state_machine: StateMachine = container.state_machine()
    state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    state_machine.mission_ongoing = True
    state_machine.current_task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("task_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(TaskStatus.Successful)
    transition = event_handler.handler(event_handler.event)

    assert transition is state_machine.starting_recharging  # type: ignore


def test_recharging_goes_to_home_when_battery_high(
    container: ApplicationContainer,
) -> None:
    state_machine: StateMachine = container.state_machine()

    recharging_state: EventHandlerBase = cast(
        EventHandlerBase, state_machine.recharging_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        recharging_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(99.9)
    transition = event_handler.handler(event_handler.event)

    assert transition is state_machine.robot_recharged  # type: ignore


def test_recharging_continues_when_battery_low(
    container: ApplicationContainer,
) -> None:
    state_machine: StateMachine = container.state_machine()

    recharging_state: EventHandlerBase = cast(
        EventHandlerBase, state_machine.recharging_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        recharging_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(10.0)
    transition = event_handler.handler(event_handler.event)

    assert transition is None


def test_state_machine_failed_dependency(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01

    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.Failed)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.Failed)

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow the state machine to transition through the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.InterventionNeeded,
        ]
    )


def test_state_machine_with_successful_collection(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread: UploaderThreadMock,
    mocker,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)

    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01
    state_machine_thread.start()
    uploader_thread.start()

    robot_service_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow enough time to run mission and return home

    expected_stored_items = 1
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_with_unsuccessful_collection(
    container: ApplicationContainer,
    mocker,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread: UploaderThreadMock,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)

    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mocker.patch.object(StubRobot, "get_inspection", return_value=None)

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01
    state_machine_thread.start()
    robot_service_thread.start()
    uploader_thread.start()

    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow enough time to run mission and return home

    expected_stored_items = 0
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_with_successful_mission_stop(
    container: ApplicationContainer,
    robot_service_thread: RobotServiceThreadMock,
    state_machine_thread: StateMachineThreadMock,
    uploader_thread: UploaderThreadMock,
    mocker,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.InProgress)

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    # Set the return home delay to a higher value than the test needs to run
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 100

    mission: Mission = Mission(
        name="Dummy misson", tasks=[StubTask.take_image() for _ in range(0, 20)]
    )

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    state_machine_thread.start()
    robot_service_thread.start()
    uploader_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    scheduling_utilities.stop_mission(mission_id="")
    time.sleep(1)  # Allow enough time to stop the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.Stopping,
            States.AwaitNextMission,
        ]
    )


def test_state_machine_with_unsuccessful_mission_stop_with_mission_id(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    caplog: pytest.LogCaptureFixture,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.InProgress)
    mocker.patch.object(
        StubRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.state_machine.sleep_time = 0

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)
    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.stop_mission(str(uuid4()))

    assert exception_details.value.status_code == HTTPStatus.NOT_FOUND.value
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.Monitor,
        ]
    )


def test_state_machine_with_unsuccessful_mission_stop(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    caplog: pytest.LogCaptureFixture,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.InProgress)
    mocker.patch.object(
        StubRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.state_machine.sleep_time = 0

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)
    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.stop_mission()

    expected_log = (
        "Be aware that the robot may still be "
        "moving even though a stop has been attempted"
    )
    assert exception_details.value.status_code == HTTPStatus.CONFLICT.value
    assert expected_log in caplog.text
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.Monitor,
            States.Stopping,
            States.Monitor,
        ]
    )


def test_state_machine_with_unsuccessful_return_home_stop(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    caplog: pytest.LogCaptureFixture,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.InProgress)
    mocker.patch.object(
        StubRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.state_machine.sleep_time = 0

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.return_home()
    time.sleep(1)
    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.stop_mission()

    expected_log = (
        "Be aware that the robot may still be "
        "moving even though a stop has been attempted"
    )
    assert exception_details.value.status_code == HTTPStatus.CONFLICT.value
    assert expected_log in caplog.text
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.ReturningHome,
            States.Stopping,
            States.ReturningHome,
        ]
    )


def test_state_machine_with_successful_return_home_stop(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.InProgress)

    state_machine_thread.state_machine.sleep_time = 0

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.return_home()
    time.sleep(1)
    scheduling_utilities.stop_mission()

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.ReturningHome,
            States.Stopping,
            States.RobotStandingStill,
        ]
    )


def test_state_machine_with_mission_start_during_return_home_without_queueing_stop_response(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Available)
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.InProgress)

    state_machine_thread.state_machine.sleep_time = 0

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.return_home()
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.ReturningHome,
            States.Stopping,
            States.RobotStandingStill,
            States.Monitor,
        ]
    )
    assert (
        not state_machine_thread.state_machine.events.api_requests.start_mission.request.has_event()
    )


def test_state_machine_with_return_home_failure_successful_retries(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    state_machine_thread.start()
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Available)
    mocker.patch.object(
        StubRobot, "task_status", side_effect=[TaskStatus.Failed, TaskStatus.Successful]
    )
    robot_service_thread.start()

    scheduling_utilities.return_home()
    time.sleep(3)  # Allow enough time to run mission and return home

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.ReturningHome,
            States.ReturningHome,
            States.Home,
            States.RobotStandingStill,
        ]
    )


def test_state_machine_with_return_home_failure_unsuccessful_retries_twice(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    state_machine_thread.start()
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Available)
    mocker.patch.object(StubRobot, "task_status", return_value=TaskStatus.Failed)
    robot_service_thread.start()

    scheduling_utilities.return_home()
    time.sleep(3)  # Allow enough time to run mission and return home
    scheduling_utilities.release_intervention_needed()
    scheduling_utilities.return_home()
    time.sleep(3)  # Allow enough time to run mission and return home

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.InterventionNeeded,
            States.UnknownStatus,
            States.RobotStandingStill,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.ReturningHome,
            States.InterventionNeeded,
        ]
    )


def test_state_machine_offline_to_robot_standing_still(
    state_machine_thread, robot_service_thread, mocker
) -> None:
    # Robot status check happens every 5 seconds by default, so we mock the behavior
    # to poll for status imediately
    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    robot_service_thread.robot_service.robot = StubRobotOfflineToRobotStandingStillTest(
        robot_service_thread.robot_service.shared_state.state
    )
    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.Offline, States.RobotStandingStill]
    )


def test_state_machine_idle_to_blocked_protective_stop_to_idle(
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    # Robot status check happens every 5 seconds by default, so we mock the behavior
    # to poll for status imediately
    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    robot_service_thread.robot_service.robot = (
        StubRobotBlockedProtectiveStopToRobotStandingStillTest(
            robot_service_thread.robot_service.shared_state.state
        )
    )

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.BlockedProtectiveStop, States.RobotStandingStill]
    )


def test_state_machine_home_to_robot_standing_still(
    mocker, state_machine_thread, robot_service_thread
) -> None:
    # Robot status check happens every 5 seconds by default, so we mock the behavior
    # to poll for status imediately
    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )
    robot_service_thread.robot_service.robot = StubRobotHomeToRobotStandingStillTest(
        robot_service_thread.robot_service.shared_state.state
    )

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.Home, States.RobotStandingStill]
    )


def test_state_machine_offline_to_home(
    mocker, state_machine_thread, robot_service_thread
) -> None:
    # Robot status check happens every 5 seconds by default, so we mock the behavior
    # to poll for status imediately
    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )
    robot_service_thread.robot_service.robot = StubRobotOfflineToHomeTest(
        robot_service_thread.robot_service.shared_state.state
    )

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.Offline, States.Home]
    )


def _mock_robot_exception_with_message() -> RobotException:
    raise RobotException(
        error_reason=ErrorReason.RobotUnknownErrorException,
        error_description="This is an example error description",
    )
