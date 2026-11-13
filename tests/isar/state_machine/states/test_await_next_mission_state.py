from collections import deque

from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from tests.test_mocks.robot_interface import StubRobot
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)
from tests.test_mocks.task import StubTask
from tests.wait import wait_until


def test_state_machine_with_successful_mission_stop(
    scheduling_utilities: SchedulingUtilities,
    robot_service_thread: RobotServiceThreadMock,
    state_machine_thread: StateMachineThreadMock,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(StubRobot, "robot_status", return_value=RobotStatus.Home)
    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )

    mocker.patch.object(settings, "ROBOT_API_BATTERY_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "ROBOT_API_STATUS_POLL_INTERVAL", 0.01)
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mocker.patch.object(settings, "RETURN_HOME_DELAY", 15)

    mission: Mission = Mission(
        id="id",
        name="Dummy misson",
        tasks=[StubTask.take_image() for _ in range(20)],
    )

    state_machine_thread.start()
    robot_service_thread.start()
    wait_until(
        lambda: States.Home in state_machine_thread.state_machine.transitions_list
    )
    scheduling_utilities.start_mission(mission=mission)
    wait_until(
        lambda: state_machine_thread.state_machine.current_state.name == States.Monitor
    )
    scheduling_utilities.stop_mission()

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.Home,
            States.Monitor,
            States.Stopping,
            States.AwaitNextMission,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )
