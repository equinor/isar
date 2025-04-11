import time
from collections import deque
from threading import Thread
from typing import List

import pytest
from pytest_mock import MockerFixture

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
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import ReturnToHome, TakeImage, Task
from tests.mocks.pose import MockPose
from tests.mocks.robot_interface import (
    MockRobot,
    MockRobotIdleToBlockedProtectiveStopToIdleTest,
    MockRobotIdleToOfflineToIdleTest,
)
from tests.mocks.task import MockTask


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


def test_initial_off(state_machine) -> None:
    assert state_machine.state == "off"


def test_reset_state_machine(state_machine) -> None:
    state_machine.reset_state_machine()

    assert state_machine.current_task is None
    assert state_machine.current_mission is None


def test_state_machine_transitions_when_running_full_mission(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    robot_service_thread.start()
    state_machine_thread.start()

    task_1: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    task_2: Task = ReturnToHome(pose=MockPose.default_pose())
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.Idle,
            States.Monitor,
            States.Idle,
        ]
    )


def test_state_machine_failed_dependency(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    mocker,
) -> None:
    task_1: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    task_2: Task = ReturnToHome(pose=MockPose.default_pose())
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    mocker.patch.object(MockRobot, "task_status", return_value=TaskStatus.Failed)

    robot_service_thread.start()
    state_machine_thread.start()

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.1)  # Allow the state machine to transition through the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.Idle,
            States.Monitor,
            States.Idle,
        ]
    )


def test_state_machine_with_successful_collection(
    container: ApplicationContainer,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread,
    mocker,
) -> None:
    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mission: Mission = Mission(name="Dummy misson", tasks=[MockTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    robot_service_thread.start()
    state_machine_thread.start()
    uploader_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.1)

    expected_stored_items = 1
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.Idle,
            States.Monitor,
            States.Idle,
        ]
    )


def test_state_machine_with_unsuccessful_collection(
    container: ApplicationContainer,
    mocker,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
    uploader_thread,
) -> None:
    robot_service_thread.start()
    uploader_thread.start()

    storage_mock: StorageInterface = container.storage_handlers(List[StorageInterface])[
        0
    ]

    mocker.patch.object(MockRobot, "get_inspection", return_value=None)

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    state_machine_thread.start()

    mission: Mission = Mission(name="Dummy misson", tasks=[MockTask.take_image()])
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.1)

    expected_stored_items = 0
    assert len(storage_mock.stored_inspections) == expected_stored_items  # type: ignore

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.Idle,
            States.Monitor,
            States.Idle,
        ]
    )


def test_state_machine_with_successful_mission_stop(
    container: ApplicationContainer,
    robot_service_thread: RobotServiceThreadMock,
    state_machine_thread: StateMachineThreadMock,
    uploader_thread,
) -> None:
    mission: Mission = Mission(
        name="Dummy misson", tasks=[MockTask.take_image() for _ in range(0, 20)]
    )

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()

    robot_service_thread.start()
    state_machine_thread.start()
    uploader_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    scheduling_utilities.stop_mission()

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.Idle, States.Monitor, States.Stop, States.Idle]
    )


def test_state_machine_with_unsuccessful_mission_stop(
    container: ApplicationContainer,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    caplog: pytest.LogCaptureFixture,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[MockTask.take_image()])

    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    mocker.patch.object(MockRobot, "task_status", return_value=TaskStatus.InProgress)
    mocker.patch.object(
        MockRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.state_machine.sleep_time = 0

    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    time.sleep(0.1)
    scheduling_utilities.stop_mission()

    expected_log = (
        "Be aware that the robot may still be "
        "moving even though a stop has been attempted"
    )
    assert expected_log in caplog.text
    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.Idle, States.Monitor, States.Stop, States.Idle]
    )


def test_state_machine_idle_to_offline_to_idle(
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    robot_service_thread.robot_service.robot = MockRobotIdleToOfflineToIdleTest(
        robot_service_thread.robot_service.shared_state.state
    )

    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(0.3)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.Idle, States.Offline, States.Idle]
    )


def test_state_machine_idle_to_blocked_protective_stop_to_idle(
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    robot_service_thread.robot_service.robot = (
        MockRobotIdleToBlockedProtectiveStopToIdleTest(
            robot_service_thread.robot_service.shared_state.state
        )
    )

    robot_service_thread.start()
    state_machine_thread.start()
    time.sleep(0.3)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.Idle, States.BlockedProtectiveStop, States.Idle]
    )


def _mock_robot_exception_with_message() -> RobotException:
    raise RobotException(
        error_reason=ErrorReason.RobotUnknownErrorException,
        error_description="This is an example error description",
    )
