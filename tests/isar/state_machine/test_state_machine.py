import time
from collections import deque
from threading import Thread
from typing import List

import pytest
from injector import Injector
from pytest_mock import MockerFixture

from isar.models.communication.queues.events import Events, SharedState
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
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from tests.mocks.pose import MockPose
from tests.mocks.robot_interface import (
    MockRobot,
    MockRobotBlockedProtectiveStopToRobotStandingStillTest,
    MockRobotHomeToRobotStandingStillTest,
    MockRobotOfflineToHomeTest,
    MockRobotOfflineToRobotStandingStillTest,
)
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
            events=self.injector.get(Events),
            storage_handlers=injector.get(List[StorageInterface]),
            mqtt_publisher=injector.get(MqttClientInterface),
        )
        self._thread: Thread = Thread(target=self.uploader.run)
        self._thread.daemon = True
        self._thread.start()


class RobotServiceThread(object):
    def __init__(self, injector) -> None:
        self.injector: Injector = injector
        self.robot_service: Robot = Robot(
            events=self.injector.get(Events),
            robot=self.injector.get(RobotInterface),
            shared_state=self.injector.get(SharedState),
        )

    def start(self):
        self._thread: Thread = Thread(target=self.robot_service.run)
        self._thread.daemon = True
        self._thread.start()

    def teardown(self):
        self.robot_service.stop()
        self._thread.join()


@pytest.fixture
def state_machine_thread(injector) -> StateMachineThread:
    return StateMachineThread(injector)


@pytest.fixture
def uploader_thread(injector) -> UploaderThread:
    return UploaderThread(injector=injector)


@pytest.fixture
def robot_service_thread(injector):
    robot_service_thread: RobotServiceThread = RobotServiceThread(injector=injector)
    yield robot_service_thread
    robot_service_thread.teardown()


def test_initial_unknown_status(state_machine) -> None:
    assert state_machine.state == "unknown_status"


def test_reset_state_machine(state_machine) -> None:
    state_machine.reset_state_machine()

    assert state_machine.current_task is None
    assert state_machine.current_mission is None


def test_state_machine_transitions_when_running_full_mission(
    injector, state_machine_thread, robot_service_thread, mocker
) -> None:
    state_machine_thread.state_machine.await_next_mission_state.return_home_delay = 0.1
    state_machine_thread.start()
    mocker.patch.object(MockRobot, "robot_status", return_value=RobotStatus.Home)
    robot_service_thread.start()
    task_1: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
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


def test_state_machine_failed_dependency(
    injector, state_machine_thread, robot_service_thread, mocker
) -> None:

    state_machine_thread.state_machine.await_next_mission_state.return_home_delay = 0.1
    state_machine_thread.start()

    mocker.patch.object(MockRobot, "task_status", return_value=TaskStatus.Failed)
    robot_service_thread.start()

    task_1: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    task_2: Task = TakeImage(
        target=MockPose.default_pose().position, robot_pose=MockPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1, task_2])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(3)  # Allow the state machine to transition through the mission

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.Monitor,
            States.AwaitNextMission,
            States.ReturningHome,
            States.RobotStandingStill,
        ]
    )


def test_state_machine_with_successful_collection(
    injector, state_machine_thread, robot_service_thread, uploader_thread, mocker
) -> None:
    mocker.patch.object(MockRobot, "robot_status", return_value=RobotStatus.Home)

    storage_mock: StorageInterface = injector.get(List[StorageInterface])[0]

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    mission: Mission = Mission(name="Dummy misson", tasks=[MockTask.take_image()])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    state_machine_thread.state_machine.await_next_mission_state.return_home_delay = 0.1
    state_machine_thread.start()
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
    injector, mocker, state_machine_thread, robot_service_thread, uploader_thread
) -> None:
    mocker.patch.object(MockRobot, "robot_status", return_value=RobotStatus.Home)
    storage_mock: StorageInterface = injector.get(List[StorageInterface])[0]

    mocker.patch.object(MockRobot, "get_inspection", return_value=[])

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    state_machine_thread.state_machine.await_next_mission_state.return_home_delay = 0.1
    state_machine_thread.start()
    robot_service_thread.start()

    mission: Mission = Mission(name="Dummy misson", tasks=[MockTask.take_image()])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

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
    injector: Injector,
    mocker,
    robot_service_thread: RobotServiceThread,
    state_machine_thread: StateMachineThread,
) -> None:
    mocker.patch.object(MockRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(MockRobot, "get_inspection", return_value=[])

    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    state_machine_thread.state_machine.await_next_mission_state.return_home_delay = 0.1
    state_machine_thread.start()
    robot_service_thread.start()

    mission: Mission = Mission(
        name="Dummy misson", tasks=[MockTask.take_image() for _ in range(0, 20)]
    )

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)
    scheduling_utilities.stop_mission()

    time.sleep(3)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.Stopping,
            States.AwaitNextMission,
            States.ReturningHome,
            States.Home,
        ]
    )


def test_state_machine_with_unsuccessful_mission_stop(
    injector: Injector,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThread,
    caplog: pytest.LogCaptureFixture,
    robot_service_thread: RobotServiceThread,
) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[MockTask.take_image()])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    mocker.patch.object(MockRobot, "task_status", return_value=TaskStatus.InProgress)
    mocker.patch.object(
        MockRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.state_machine.sleep_time = 0
    state_machine_thread.state_machine.await_next_mission_state.return_home_delay = 10  # Return home delay is set to 10 seconds to avoid the state machine triggering return home within the test duration
    state_machine_thread.start()
    robot_service_thread.start()

    scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)
    scheduling_utilities.stop_mission()
    time.sleep(3)

    expected_log = (
        "Be aware that the robot may still be "
        "moving even though a stop has been attempted"
    )
    assert expected_log in caplog.text
    assert state_machine_thread.state_machine.transitions_list == deque(
        [
            States.UnknownStatus,
            States.RobotStandingStill,
            States.Monitor,
            States.Stopping,
            States.AwaitNextMission,
        ]
    )


def test_state_machine_offline_to_robot_standing_still(
    mocker, state_machine_thread, robot_service_thread
) -> None:
    # Robot status check happens every 5 seconds by default, so we mock the behavior
    # to poll for status imediately
    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )

    robot_service_thread.robot_service.robot = MockRobotOfflineToRobotStandingStillTest(
        robot_service_thread.robot_service.shared_state.state
    )
    state_machine_thread.start()
    robot_service_thread.start()
    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.Offline, States.RobotStandingStill]
    )


def test_state_machine_blocked_protective_stop_to_robot_standing_still(
    mocker, state_machine_thread, robot_service_thread
) -> None:
    # Robot status check happens every 5 seconds by default, so we mock the behavior
    # to poll for status imediately
    mocker.patch.object(
        RobotStatusThread, "_is_ready_to_poll_for_status", return_value=True
    )
    robot_service_thread.robot_service.robot = (
        MockRobotBlockedProtectiveStopToRobotStandingStillTest(
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
    robot_service_thread.robot_service.robot = MockRobotHomeToRobotStandingStillTest(
        robot_service_thread.robot_service.shared_state.state
    )

    robot_service_thread.start()
    state_machine_thread.start()
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
    robot_service_thread.robot_service.robot = MockRobotOfflineToHomeTest(
        robot_service_thread.robot_service.shared_state.state
    )

    robot_service_thread.start()
    state_machine_thread.start()
    time.sleep(1)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.Offline, States.Home]
    )


def _mock_robot_exception_with_message() -> RobotException:
    raise RobotException(
        error_reason=ErrorReason.RobotUnknownErrorException,
        error_description="This is an example error description",
    )
