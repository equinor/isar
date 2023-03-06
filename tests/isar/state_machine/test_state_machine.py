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
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.services.utilities.threaded_request import ThreadedRequest
from isar.state_machine.state_machine import StateMachine, main
from isar.state_machine.states_enum import States
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader
from robot_interface.models.exceptions import RobotException
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import StepStatus
from robot_interface.models.mission.step import DriveToPose, Step, TakeImage
from robot_interface.models.mission.task import Task
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from tests.mocks.pose import MockPose
from tests.mocks.robot_interface import MockRobot
from tests.mocks.step import MockStep


class StateMachineThread(object):
    def __init__(self, injector) -> None:
        self.injector: Injector = injector
        self.state_machine: StateMachine = injector.get(StateMachine)
        self._thread: Thread = Thread(target=main, args=[self.state_machine])
        self._thread.daemon = True
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

    assert state_machine.current_step is None
    assert state_machine.current_task is None
    assert state_machine.current_mission is None


empty_mission: Mission = Mission([], None)


def test_state_machine_transitions(injector, state_machine_thread) -> None:
    step: Step = DriveToPose(pose=MockPose.default_pose)
    mission: Mission = Mission(tasks=[Task(steps=[step])])  # type: ignore
    metadata: MissionMetadata = MissionMetadata(mission.id)
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(
        mission=mission, initial_pose=None, mission_metadata=metadata
    )

    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.InitiateStep,
            States.Monitor,
            States.InitiateStep,
            States.Idle,
        ]
    )
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_failed_dependency(
    injector, state_machine_thread, mocker
) -> None:
    drive_to_step: Step = DriveToPose(pose=MockPose.default_pose)
    inspection_step: Step = MockStep.take_image_in_coordinate_direction
    mission: Mission = Mission(tasks=[Task(steps=[drive_to_step, inspection_step])])  # type: ignore
    metadata: MissionMetadata = MissionMetadata(mission.id)

    mocker.patch.object(MockRobot, "step_status", return_value=StepStatus.Failed)

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(
        mission=mission, initial_pose=None, mission_metadata=metadata
    )

    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.InitiateStep,
            States.Monitor,
            States.InitiateStep,
            States.Idle,
        ]
    )
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_with_successful_collection(
    injector, state_machine_thread, uploader_thread
) -> None:
    storage_mock: StorageInterface = injector.get(List[StorageInterface])[0]

    step: TakeImage = MockStep.take_image_in_coordinate_direction
    mission: Mission = Mission(tasks=[Task(steps=[step])])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    metadata: MissionMetadata = MissionMetadata(mission.id)

    scheduling_utilities.start_mission(
        mission=mission, initial_pose=None, mission_metadata=metadata
    )
    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.InitiateStep,
            States.Monitor,
            States.InitiateStep,
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

    mocker.patch.object(MockRobot, "get_inspections", return_value=[])

    step: TakeImage = MockStep.take_image_in_coordinate_direction
    mission: Mission = Mission(tasks=[Task(steps=[step])])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    metadata: MissionMetadata = MissionMetadata(mission.id)

    scheduling_utilities.start_mission(
        mission=mission, initial_pose=None, mission_metadata=metadata
    )
    time.sleep(3)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Initialize,
            States.InitiateStep,
            States.Monitor,
            States.InitiateStep,
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
    step: TakeImage = MockStep.take_image_in_coordinate_direction
    mission: Mission = Mission(tasks=[Task(steps=[step])])
    metadata: MissionMetadata = MissionMetadata(mission.id)
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(
        mission=mission, initial_pose=None, mission_metadata=metadata
    )
    scheduling_utilities.stop_mission()
    expected = deque(
        [
            States.Idle,
            States.Initialize,
            States.InitiateStep,
            States.StopStep,
            States.Idle,
        ]
    )
    actual = state_machine_thread.state_machine.transitions_list
    unexpected_log = (
        "Could not communicate request: Reached limit for stop attempts. "
        "Cancelled mission and transitioned to idle."
    )
    assert unexpected_log not in caplog.text
    assert expected == actual


def test_state_machine_with_unsuccsessful_mission_stop(
    injector: Injector,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThread,
    caplog: pytest.LogCaptureFixture,
) -> None:
    step: TakeImage = MockStep.take_image_in_coordinate_direction
    mission: Mission = Mission(tasks=[Task(steps=[step])])
    metadata: MissionMetadata = MissionMetadata(mission.id)
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    scheduling_utilities.start_mission(
        mission=mission, initial_pose=None, mission_metadata=metadata
    )
    mocker.patch.object(ThreadedRequest, "get_output", side_effect=RobotException)
    scheduling_utilities.stop_mission()
    expected = deque(
        [
            States.Idle,
            States.Initialize,
            States.InitiateStep,
            States.StopStep,
            States.Idle,
        ]
    )
    actual = state_machine_thread.state_machine.transitions_list
    expected_log = (
        "Could not communicate request: Reached limit for stop attempts. "
        "Cancelled mission and transitioned to idle."
    )
    assert expected_log in caplog.text
    assert expected == actual
