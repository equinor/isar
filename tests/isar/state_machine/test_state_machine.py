import time
from collections import deque
from pathlib import Path
from threading import Thread

import pytest
from injector import Injector

from isar.mission_planner.local_planner import LocalPlanner
from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine, main
from isar.state_machine.states_enum import States
from isar.storage.storage_interface import StorageInterface
from robot_interface.models.mission import DriveToPose, TakeImage, Task
from robot_interface.models.mission.status import TaskStatus
from tests.mocks.robot_interface import MockRobot
from tests.mocks.robot_variables import mock_pose
from tests.mocks.task import MockTask


class StateMachineThread(object):
    def __init__(self, injector) -> None:
        self.injector: Injector = injector
        self.state_machine: StateMachine = injector.get(StateMachine)
        self._thread: Thread = Thread(target=main, args=[injector])
        self._thread.daemon = True
        self._thread.start()


@pytest.fixture
def state_machine_thread(injector) -> StateMachineThread:
    return StateMachineThread(injector)


def get_mission():
    mission_reader: LocalPlanner = LocalPlanner()
    mission: Mission = mission_reader.read_mission_from_file(
        Path("./tests/test_data/test_mission_working.json")
    )
    return mission


def test_initial_off(state_machine):
    assert state_machine.state == "off"


@pytest.mark.parametrize("should_send, expected_output", [(True, True), (False, False)])
def test_should_send_status(state_machine, should_send, expected_output):
    if should_send is not None:
        state_machine.queues.mission_status.input.put(should_send)
    send: bool = state_machine.should_send_status()

    assert send is expected_output


def test_send_status(state_machine):
    state_machine.send_status()
    message = state_machine.queues.mission_status.output.get()
    assert message


def test_reset_state_machine(state_machine):
    next_state = state_machine.reset_state_machine()

    assert not state_machine.mission_in_progress
    assert state_machine.current_task is None
    assert state_machine.current_mission.tasks == []
    assert next_state is States.Idle


@pytest.mark.parametrize(
    "mission, mission_in_progress, expected_output",
    [
        (None, True, (False, None)),
        (Mission([], None), True, (False, None)),
        (Mission([], None), False, (True, Mission([], None))),
    ],
)
def test_should_start_mission(
    state_machine, mission, mission_in_progress, expected_output
):
    state_machine.queues.start_mission.input.put(mission)
    state_machine.mission_in_progress = mission_in_progress
    output = state_machine.should_start_mission()

    assert output == expected_output


def test_start_mission(state_machine):
    state_machine.start_mission(1)
    message = state_machine.queues.start_mission.output.get()
    assert state_machine.mission_in_progress
    assert message


@pytest.mark.parametrize(
    "should_stop, mission_in_progress, expected_output",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, False),
        (None, False, False),
        (None, True, False),
    ],
)
def test_should_stop_mission(
    state_machine, should_stop, mission_in_progress, expected_output
):
    if should_stop is not None:
        state_machine.queues.stop_mission.input.put(should_stop)

    state_machine.mission_in_progress = mission_in_progress
    start: bool = state_machine.should_stop_mission()

    assert start is expected_output


def test_stop_mission(state_machine):
    state_machine.stop_mission()
    message = state_machine.queues.stop_mission.output.get()
    assert not state_machine.mission_in_progress
    assert message


def test_state_machine_transitions(injector, state_machine_thread):
    task: Task = DriveToPose(pose=mock_pose())
    mission: Mission = Mission([task])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started

    time.sleep(1)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Send,
            States.Monitor,
            States.Send,
            States.Cancel,
            States.Idle,
        ]
    )
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_failed_dependency(injector, state_machine_thread, mocker):
    driveto_task: Task = DriveToPose(pose=mock_pose())
    inspection_task: Task = MockTask.take_image_in_coordinate_direction()
    mission: Mission = Mission([driveto_task, inspection_task])
    mission.set_task_dependencies()

    mocker.patch.object(MockRobot, "task_status", return_value=TaskStatus.Failed)

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started

    time.sleep(1)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Send,
            States.Monitor,
            States.Send,
            States.Cancel,
            States.Idle,
        ]
    )
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_with_successful_collection(injector, state_machine_thread):
    storage_mock: StorageInterface = injector.get(StorageInterface)

    task: TakeImage = MockTask.take_image_in_coordinate_direction()
    mission: Mission = Mission([task])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started
    time.sleep(1)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Send,
            States.Monitor,
            States.Send,
            States.Cancel,
            States.Idle,
        ]
    )
    expected_stored_items = 3
    assert len(storage_mock.paths) == expected_stored_items
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )


def test_state_machine_with_unsuccessful_collection(
    injector, mocker, state_machine_thread
):
    storage_mock: StorageInterface = injector.get(StorageInterface)

    mocker.patch.object(MockRobot, "get_inspections", return_value=[])

    task: TakeImage = MockTask.take_image_in_coordinate_direction()
    mission: Mission = Mission([task])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started
    time.sleep(1)
    expected_transitions_list = deque(
        [
            States.Idle,
            States.Send,
            States.Monitor,
            States.Send,
            States.Cancel,
            States.Idle,
        ]
    )
    expected_stored_items = 0
    assert len(storage_mock.paths) == expected_stored_items
    print(state_machine_thread.state_machine.transitions_list)
    assert (
        state_machine_thread.state_machine.transitions_list == expected_transitions_list
    )
