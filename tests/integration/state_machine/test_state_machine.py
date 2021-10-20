import time
from threading import Thread

import pytest

from isar.models.mission import Mission
from isar.services.service_connections.mqtt.mqtt_service import MQTTService
from isar.services.service_connections.mqtt.mqtt_service_interface import (
    MQTTServiceInterface,
)
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine, States, main
from isar.storage.storage_interface import StorageInterface
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.position import Position
from robot_interface.models.mission import DriveToPose, MissionStatus, Step
from robot_interface.models.mission.step import TakeImage
from robot_interface.robot_interface import RobotInterface
from tests.mocks.blob_storage import StorageMock
from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot
from tests.test_utilities.mock_models.mock_robot_variables import mock_pose


def start_state_machine_in_thread(injector) -> StateMachine:
    state_machine_thread: Thread = Thread(target=main, args=[injector])
    state_machine_thread.daemon = True
    state_machine_thread.start()
    state_machine: StateMachine = injector.get(StateMachine)
    return state_machine


@pytest.mark.integration
def test_state_machine(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    injector.binder.bind(MQTTServiceInterface, to=MQTTService())
    state_machine: StateMachine = start_state_machine_in_thread(injector)

    step: Step = DriveToPose(pose=mock_pose())
    mission: Mission = Mission([step])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started

    time.sleep(1)
    assert state_machine.current_state is States.Monitor

    mocker.patch.object(
        MockRobot, "mission_status", return_value=MissionStatus.Completed
    )
    time.sleep(1)
    assert state_machine.current_state is States.Idle


@pytest.mark.integration
def test_state_machine_with_unsuccessful_send(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    injector.binder.bind(MQTTServiceInterface, to=MQTTService())
    state_machine: StateMachine = start_state_machine_in_thread(injector)

    step: Step = DriveToPose(pose=mock_pose())
    mission: Mission = Mission([step])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    mocker.patch.object(MockRobot, "schedule_step", return_value=(False, 1, None))

    message, _ = scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)

    assert state_machine.current_state is States.Idle


@pytest.mark.integration
def test_state_machine_with_delayed_successful_send(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    injector.binder.bind(MQTTServiceInterface, to=MQTTService())
    state_machine: StateMachine = start_state_machine_in_thread(injector)

    step: Step = DriveToPose(pose=mock_pose())
    mission: Mission = Mission([step])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    mocker.patch.object(
        MockRobot, "schedule_step", side_effect=([(False, 1, None), (True, 1, None)])
    )

    message, _ = scheduling_utilities.start_mission(mission=mission)
    print(message)
    time.sleep(1)

    assert state_machine.current_state is States.Monitor


@pytest.mark.integration
def test_data_offload(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    injector.binder.bind(StorageInterface, to=StorageMock())
    injector.binder.bind(MQTTServiceInterface, to=MQTTService())

    state_machine: StateMachine = start_state_machine_in_thread(injector=injector)

    step_1: DriveToPose = DriveToPose(pose=mock_pose())
    step_2: TakeImage = TakeImage(target=Position(x=1, y=1, z=1, frame=Frame.Robot))
    step_3: TakeImage = TakeImage(target=Position(x=1, y=1, z=1, frame=Frame.Robot))
    step_4: DriveToPose = DriveToPose(pose=mock_pose())

    mission: Mission = Mission([step_1, step_2, step_3, step_4])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started

    time.sleep(1)
    assert state_machine.current_state is States.Monitor
    assert state_machine.current_mission_step == step_1

    mocker.patch.object(
        MockRobot,
        "mission_status",
        side_effect=[MissionStatus.Completed] + 10 * [MissionStatus.InProgress],
    )
    time.sleep(1)
    assert state_machine.current_state is States.Monitor
    assert state_machine.current_mission_step == step_2

    mocker.patch.object(
        MockRobot,
        "mission_status",
        side_effect=[MissionStatus.Completed] + 10 * [MissionStatus.InProgress],
    )

    time.sleep(1)
    assert state_machine.current_state is States.Monitor
    assert state_machine.current_mission_step == step_3
    assert len(state_machine.mission_schedule.inspections) == 1

    mocker.patch.object(
        MockRobot,
        "mission_status",
        side_effect=[MissionStatus.Completed] + 10 * [MissionStatus.InProgress],
    )
    time.sleep(1)
    assert state_machine.current_state is States.Monitor
    assert state_machine.current_mission_step == step_4
    assert len(state_machine.mission_schedule.inspections) == 2

    mocker.patch.object(
        MockRobot, "mission_status", side_effect=[MissionStatus.Completed]
    )
    time.sleep(1)

    assert state_machine.current_state is States.Idle
