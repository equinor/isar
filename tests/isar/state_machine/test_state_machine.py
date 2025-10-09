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
from isar.state_machine.transitions.functions.stop import stop_mission_failed
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import ReturnToHome, TakeImage, Task
from tests.test_double.pose import DummyPose
from tests.test_double.robot_interface import (
    StubRobot,
    StubRobotBlockedProtectiveStopToHomeTest,
    StubRobotOfflineToHomeTest,
    StubRobotRobotStatusBusyIfNotHomeOrUnknownStatus,
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
) -> None:
    state_machine_thread.state_machine.await_next_mission_state.timers[
        0
    ].timeout_in_seconds = 0.01

    robot_service_thread.robot_service.robot = (
        StubRobotRobotStatusBusyIfNotHomeOrUnknownStatus(
            current_state=robot_service_thread.robot_service.shared_state.state,
            initiate_mission_delay=1,
        )
    )
    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)
    # Setting the poll interval to a lower value to ensure that the robot status is
    # updated during the mission. This value needs to be set after the robot service
    # thread has been started.
    robot_service_thread.robot_service.robot_status_thread.robot_status_poll_interval = (
        0.5
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy mission", tasks=[task_1, task_2])

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
    time.sleep(1)
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
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    events = sync_state_machine.events

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
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
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    await_next_mission_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.await_next_mission_state
    )
    timer: Optional[TimeoutHandlerMapping] = (
        await_next_mission_state.get_event_timer_by_name("should_return_home_timer")
    )

    assert timer is not None

    transition = timer.handler()

    assert transition is sync_state_machine.request_return_home  # type: ignore


def test_monitor_goes_to_return_home_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.current_task = task_1

    monitor_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.monitor_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(10.0, timeout=1)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.stop  # type: ignore
    assert not sync_state_machine.events.mqtt_queue.empty()

    mqtt_message = sync_state_machine.events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED
    assert sync_state_machine.events.mqtt_queue.get()[0]


def test_return_home_goes_to_recharging_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)

    sync_state_machine.mission_ongoing = True
    sync_state_machine.current_task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("task_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(TaskStatus.Successful)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.starting_recharging  # type: ignore


def test_recharging_goes_to_home_when_battery_high(
    sync_state_machine: StateMachine,
) -> None:
    recharging_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.recharging_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        recharging_state.get_event_handler_by_name("robot_battery_update_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(99.9)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.robot_recharged  # type: ignore


def test_recharging_continues_when_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    recharging_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.recharging_state
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
    time.sleep(1)
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow the state machine to transition through the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
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
    time.sleep(1)
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
    time.sleep(1)
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
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.5)
    scheduling_utilities.stop_mission(mission_id=mission.id)
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
            States.Home,
            States.Monitor,
        ]
    )


def test_state_machine_with_unsuccessful_mission_stop(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
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
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.5)
    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.stop_mission()

    assert exception_details.value.status_code == HTTPStatus.CONFLICT.value
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.Stopping,
            States.Monitor,
        ]
    )


def test_api_with_unsuccessful_return_home_stop(
    container: ApplicationContainer,
    sync_state_machine: StateMachine,
) -> None:
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    stop_mission_failed(sync_state_machine)

    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.stop_mission()

    assert exception_details.value.status_code == HTTPStatus.CONFLICT.value


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
    time.sleep(1)
    scheduling_utilities.return_home()
    time.sleep(1)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.ReturningHome,
            States.StoppingReturnHome,
            States.Monitor,
        ]
    )
    assert (
        not state_machine_thread.state_machine.events.api_requests.start_mission.request.has_event()
    )


def test_return_home_cancelled_when_new_mission_received(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("start_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.stop_return_home  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.stopping_return_home_state.name  # type: ignore


def test_transitioning_to_returning_home_from_stopping_when_return_home_failed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.state = sync_state_machine.stopping_return_home_state.name  # type: ignore

    stopping_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)
    transition()

    assert transition is sync_state_machine.request_return_home  # type: ignore
    assert sync_state_machine.state is sync_state_machine.returning_home_state.name  # type: ignore


def test_mission_stopped_when_going_to_lockdown(
    sync_state_machine: StateMachine, mocker: MockerFixture
) -> None:
    mocker.patch.object(StateMachine, "_finalize", return_value=None)
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.monitor_state.name  # type: ignore

    monitor_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.monitor_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.stop_go_to_lockdown  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.stopping_go_to_lockdown_state.name  # type: ignore


def test_stopping_lockdown_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.stopping_go_to_lockdown_state.name  # type: ignore

    stopping_go_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_go_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_lockdown_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.request_lockdown_mission  # type: ignore
    assert (
        sync_state_machine.events.api_requests.send_to_lockdown.response.check().lockdown_started
    )

    assert not sync_state_machine.events.mqtt_queue.empty()
    mqtt_message = sync_state_machine.events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED

    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore


def test_stopping_lockdown_failing(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
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


def test_return_home_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.go_to_lockdown  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore


def test_going_to_lockdown_transitions_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    sync_state_machine.current_task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.going_to_lockdown_state.name  # type: ignore

    going_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("task_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(TaskStatus.Successful)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.reached_lockdown  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.lockdown_state.name  # type: ignore


def test_going_to_lockdown_task_failed_transitions_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.going_to_lockdown_state.name  # type: ignore

    going_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("task_status_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(TaskStatus.Failed)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.lockdown_mission_failed  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_going_to_lockdown_mission_failed_transitions_to_intervention_needed(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.going_to_lockdown_state.name  # type: ignore

    going_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_failed_event")
    )

    assert event_handler is not None

    # The type of error reason is not important for this test
    event_handler.event.trigger_event(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.lockdown_mission_failed  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_lockdown_transitions_to_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.state = sync_state_machine.lockdown_state.name  # type: ignore

    lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        lockdown_state.get_event_handler_by_name("release_from_lockdown")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.release_from_lockdown  # type: ignore
    assert sync_state_machine.events.api_requests.release_from_lockdown.response.check()
    transition()
    assert sync_state_machine.state is sync_state_machine.home_state.name  # type: ignore


def test_lockdown_transitions_to_recharing_if_battery_low(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.lockdown_state.name  # type: ignore

    lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        lockdown_state.get_event_handler_by_name("release_from_lockdown")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.starting_recharging  # type: ignore
    assert sync_state_machine.events.api_requests.release_from_lockdown.response.check()
    transition()
    assert sync_state_machine.state is sync_state_machine.recharging_state.name  # type: ignore


def test_await_next_mission_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.await_next_mission_state.name  # type: ignore

    await_next_mission_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.await_next_mission_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        await_next_mission_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.request_lockdown_mission  # type: ignore
    assert sync_state_machine.events.api_requests.send_to_lockdown.response.check()
    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore


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

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)
    transition()

    assert transition is sync_state_machine.request_mission_start  # type: ignore
    assert sync_state_machine.state is sync_state_machine.monitor_state.name  # type: ignore


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
    mocker.patch.object(
        StubRobot,
        "robot_status",
        side_effect=[RobotStatus.Available, RobotStatus.Home],
    )
    mocker.patch.object(
        StubRobot, "task_status", side_effect=[TaskStatus.Failed, TaskStatus.Successful]
    )
    robot_service_thread.start()
    time.sleep(1)
    scheduling_utilities.return_home()
    time.sleep(3)  # Allow enough time to run mission and return home

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.ReturningHome,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_offline_to_home(
    state_machine_thread, robot_service_thread, mocker
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

    robot_service_thread.robot_service.robot = StubRobotBlockedProtectiveStopToHomeTest(
        robot_service_thread.robot_service.shared_state.state
    )

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.BlockedProtectiveStop, States.Home]
    )


def _mock_robot_exception_with_message() -> RobotException:
    raise RobotException(
        error_reason=ErrorReason.RobotUnknownErrorException,
        error_description="This is an example error description",
    )


def test_transition_from_monitor_to_pausing(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.state = sync_state_machine.monitor_state.name  # type: ignore

    monitor_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.monitor_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        monitor_state.get_event_handler_by_name("pause_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.pause  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.pausing_state.name  # type: ignore


def test_transition_from_pausing_to_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.state = sync_state_machine.pausing_state.name  # type: ignore

    pausing_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_state.get_event_handler_by_name("successful_pause_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_paused  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.paused_state.name  # type: ignore


def test_transition_from_pausing_to_monitor(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.state = sync_state_machine.pausing_state.name  # type: ignore

    pausing_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_state.get_event_handler_by_name("failed_pause_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.mission_pausing_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.monitor_state.name  # type: ignore


def test_transition_from_returning_home_to_pausing_return_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("pause_mission_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.pause_return_home  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.pausing_return_home_state.name  # type: ignore


def test_transition_from_pausing_return_home_to_return_home_paused(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.state = sync_state_machine.pausing_return_home_state.name  # type: ignore

    pausing_return_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_return_home_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_mission_paused  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.return_home_paused_state.name  # type: ignore


def test_transition_from_pausing_return_home_to_returning_home(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.mission_ongoing = True
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.current_task = task_1
    sync_state_machine.current_mission = Mission(name="Dummy misson", tasks=[task_1])
    sync_state_machine.state = sync_state_machine.pausing_return_home_state.name  # type: ignore

    pausing_return_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.pausing_return_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        pausing_return_home_state.get_event_handler_by_name("failed_pause_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.return_home_mission_pausing_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.returning_home_state.name  # type: ignore
