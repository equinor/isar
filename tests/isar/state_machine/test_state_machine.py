import time
from collections import deque
from pathlib import Path
from threading import Thread
from typing import List

import pytest
from injector import Injector
from pytest_mock import MockerFixture

from isar.mission_planner.local_planner import LocalPlanner
from isar.models.communication.queues.queues import Queues
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
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import ReturnToHome, TakeImage
from robot_interface.models.mission.task import Task
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from tests.mocks.pose import MockPose
from tests.mocks.robot_interface import MockRobot, MockRobotIdleToOfflineToIdleTest
from tests.mocks.task import MockTask


class StateMachineThread(object):
    def __init__(self, injector) -> None:
        self.injector: Injector = injector
        self.state_machine: StateMachine = injector.get(StateMachine)
        self._thread: Thread = Thread(target=main, args=[self.state_machine])
        self._thread.daemon = True

    def start(self):
        self._thread.start()


class UploaderThread(object):
    def __init__(self, injector) -> None:
        self.injector: Injector = injector
        self.uploader: Uploader = Uploader(
            queues=self.injector.get(Queues),
            storage_handlers=injector.get(List[StorageInterface]),
            mqtt_publisher=injector.get(MqttClientInterface),
        )
        self._thread: Thread = Thread(target=self.uploader.run)
        self._thread.daemon = True
        self._thread.start()


@pytest.fixture
def state_machine_thread(injector) -> StateMachineThread:
    return StateMachineThread(injector)


@pytest.fixture
def uploader_thread(injector) -> UploaderThread:
    return UploaderThread(injector=injector)


def get_mission() -> Mission:
    mission_reader: LocalPlanner = LocalPlanner()
    mission: Mission = mission_reader.read_mission_from_file(
        Path("./tests/test_data/test_mission_working.json")
    )
    return mission


def test_initial_off(state_machine) -> None:
    assert state_machine.state == "off"


def test_send_status(state_machine) -> None:
    state_machine.send_state_status()
    message = state_machine.queues.state.check()
    assert message == state_machine.current_state


def test_reset_state_machine(state_machine) -> None:
    state_machine.reset_state_machine()

    assert state_machine.current_task is None
    assert state_machine.current_mission is None


empty_mission: Mission = Mission([], None)


@pytest.mark.parametrize(
    "should_run_by_task",
    [
        (True),
        (False),
    ],
)
def test_state_machine_transitions(
    injector, state_machine_thread, should_run_by_task
) -> None:
    task_1: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    task_2: Task = ReturnToHome(pose=MockPose.default_pose())
    mission: Mission = Mission(tasks=[task_1, task_2])  # type: ignore

    state_machine_thread.state_machine.run_mission_by_task = should_run_by_task
    state_machine_thread.start()

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(mission=mission, initial_pose=None)

    time.sleep(3)
    if should_run_by_task:
        expected_transitions_list = deque(
            [
                States.Idle,
                States.Initialize,
                States.Initiate,
                States.Monitor,
                States.Initiate,
                States.Monitor,
                States.Initiate,
                States.Idle,
            ]
        )
    else:
        expected_transitions_list = deque(
            [
                States.Idle,
                States.Initialize,
                States.Initiate,
                States.Monitor,
                States.Initiate,
                States.Idle,
            ]
        )
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_transitions_when_running_full_mission(
    injector, state_machine_thread
) -> None:
    state_machine_thread.state_machine.run_mission_by_task = False
    state_machine_thread.start()

    task_1: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    task_2: Task = ReturnToHome(pose=MockPose.default_pose())
    mission: Mission = Mission(tasks=[task_1, task_2])  # type: ignore

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(mission=mission, initial_pose=None)

    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.Initiate,
            States.Monitor,
            States.Initiate,
            States.Idle,
        ]
    )
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_failed_dependency(
    injector, state_machine_thread, mocker
) -> None:
    task_1: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    task_2: Task = ReturnToHome(pose=MockPose.default_pose())
    mission: Mission = Mission(tasks=[task_1, task_2])  # type: ignore

    mocker.patch.object(MockRobot, "task_status", return_value=TaskStatus.Failed)

    state_machine_thread.state_machine.run_mission_by_task = True

    state_machine_thread.start()

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(mission=mission, initial_pose=None)

    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.Initiate,
            States.Monitor,
            States.Initiate,
            States.Monitor,
            States.Initiate,
            States.Idle,
        ]
    )
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_with_successful_collection(
    injector, state_machine_thread, uploader_thread
) -> None:
    state_machine_thread.start()

    storage_mock: StorageInterface = injector.get(List[StorageInterface])[0]

    mission: Mission = Mission(tasks=[MockTask.take_image()])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    scheduling_utilities.start_mission(mission=mission, initial_pose=None)
    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.Initiate,
            States.Monitor,
            States.Initiate,
            States.Idle,
        ]
    )
    expected_stored_items = 1
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_with_unsuccessful_collection(
    injector, mocker, state_machine_thread
) -> None:
    storage_mock: StorageInterface = injector.get(List[StorageInterface])[0]

    mocker.patch.object(MockRobot, "get_inspection", return_value=[])

    state_machine_thread.start()

    mission: Mission = Mission(tasks=[MockTask.take_image()])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    scheduling_utilities.start_mission(mission=mission, initial_pose=None)
    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.Initiate,
            States.Monitor,
            States.Initiate,
            States.Idle,
        ]
    )
    expected_stored_items = 0
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore
    print(state_machine_thread.state_machine.transitions_list)
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_with_successful_mission_stop(
    injector: Injector,
    state_machine_thread: StateMachineThread,
    caplog: pytest.LogCaptureFixture,
) -> None:
    state_machine_thread.start()

    mission: Mission = Mission(tasks=[MockTask.take_image()])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(mission=mission, initial_pose=None)
    scheduling_utilities.stop_mission()
    time.sleep(3)

    actual = state_machine_thread.state_machine.transitions_list
    unexpected_log = (
        "Could not communicate request: Reached limit for stop attempts. "
        "Cancelled mission and transitioned to idle."
    )
    assert unexpected_log not in caplog.text
    assert States.Idle == actual.pop()
    assert States.Stop == actual.pop()


def test_state_machine_with_unsuccessful_mission_stop(
    injector: Injector,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThread,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mission: Mission = Mission(tasks=[MockTask.take_image()])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    mocker.patch.object(MockRobot, "task_status", return_value=TaskStatus.InProgress)
    mocker.patch.object(
        MockRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.start()

    scheduling_utilities.start_mission(mission=mission, initial_pose=None)

    scheduling_utilities.stop_mission()

    expected = deque(
        [
            States.Idle,
            States.Initialize,
            States.Initiate,
            States.Stop,
            States.Idle,
        ]
    )
    actual = state_machine_thread.state_machine.transitions_list
    expected_log = (
        "Be aware that the robot may still be "
        "moving even though a stop has been attempted"
    )
    assert expected_log in caplog.text
    assert expected == actual


def test_state_machine_idle_to_offline_to_idle(state_machine_thread) -> None:
    state_machine_thread.state_machine.robot = MockRobotIdleToOfflineToIdleTest()

    state_machine_thread.start()
    # Robot status check happens every 5 seconds by default
    time.sleep(13)  # Ensure that robot_status have been called again in Idle

    expected_transitions_list = deque([States.Idle, States.Offline, States.Idle])
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def _mock_robot_exception_with_message() -> RobotException:
    raise RobotException(
        error_reason=ErrorReason.RobotUnknownErrorException,
        error_description="This is an example error description",
    )
