import time
from threading import Thread

from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine, States, main
from robot_interface.models.mission import DriveToPose, MissionStatus, Step
from robot_interface.robot_interface import RobotInterface
from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot
from tests.test_utilities.mock_models.mock_robot_variables import mock_pose


def start_state_machine_in_thread(injector) -> StateMachine:
    state_machine_thread: Thread = Thread(target=main, args=[injector])
    state_machine_thread.daemon = True
    state_machine_thread.start()
    state_machine: StateMachine = injector.get(StateMachine)
    return state_machine


def test_state_machine(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    state_machine: StateMachine = start_state_machine_in_thread(injector)

    step: Step = DriveToPose(pose=mock_pose())
    mission: Mission = Mission([step])

    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)
    message, _ = scheduling_utilities.start_mission(mission=mission)
    assert message.started

    time.sleep(1)
    assert state_machine.status.current_state is States.Monitor

    mocker.patch.object(
        MockRobot, "mission_status", return_value=MissionStatus.Completed
    )
    time.sleep(1)
    assert state_machine.status.current_state is States.Idle


def test_state_machine_with_unsuccessful_send(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    state_machine: StateMachine = start_state_machine_in_thread(injector)

    step: Step = DriveToPose(pose=mock_pose())
    mission: Mission = Mission([step])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    mocker.patch.object(MockRobot, "schedule_step", return_value=(False, 1, None))

    message, _ = scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)

    assert state_machine.status.current_state is States.Idle


def test_state_machine_with_delayed_successful_send(injector, mocker):
    injector.binder.bind(RobotInterface, to=MockRobot())
    state_machine: StateMachine = start_state_machine_in_thread(injector)

    step: Step = DriveToPose(pose=mock_pose())
    mission: Mission = Mission([step])
    scheduling_utilities: SchedulingUtilities = injector.get(SchedulingUtilities)

    mocker.patch.object(
        MockRobot, "schedule_step", side_effect=([(False, 1, None), (True, 1, None)])
    )

    message, _ = scheduling_utilities.start_mission(mission=mission)
    time.sleep(1)

    assert state_machine.status.current_state is States.Monitor
