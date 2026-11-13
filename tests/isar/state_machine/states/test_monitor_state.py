from collections import deque

from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorReason,
    RobotException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from tests.test_mocks.robot_interface import (
    StubRobot,
    StubRobotMissionStatusRaisesException,
)
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
)
from tests.test_mocks.task import StubTask
from tests.wait import wait_until


def _mock_robot_exception_with_message() -> RobotException:
    raise RobotException(
        error_reason=ErrorReason.RobotUnknownErrorException,
        error_description="This is an example error description",
    )


def test_state_machine_with_unsuccessful_mission_stop(
    scheduling_utilities: SchedulingUtilities,
    mocker: MockerFixture,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mocker.patch.object(settings, "FSM_SLEEP_TIME", 0.01)
    mission: Mission = Mission(
        id="id", name="Dummy misson", tasks=[StubTask.take_image()]
    )

    mocker.patch.object(
        StubRobot, "mission_status", return_value=MissionStatus.InProgress
    )
    mocker.patch.object(
        StubRobot, "stop", side_effect=_mock_robot_exception_with_message
    )

    state_machine_thread.start()
    robot_service_thread.start()
    wait_until(
        lambda: States.AwaitNextMission
        in state_machine_thread.state_machine.transitions_list,
        timeout=10,
    )
    scheduling_utilities.start_mission(mission=mission)
    wait_until(
        lambda: state_machine_thread.state_machine.current_state.name == States.Monitor
    )
    scheduling_utilities.stop_mission()

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.Stopping,
            States.Monitor,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )


def test_robot_mission_status_exception_handling(
    scheduling_utilities: SchedulingUtilities,
    state_machine_thread: StateMachineThreadMock,
    robot_service_thread: RobotServiceThreadMock,
) -> None:
    mission = Mission(
        id="id",
        name="Dummy mission",
        tasks=[StubTask.take_image()],
    )

    robot_service_thread.robot_service.robot = StubRobotMissionStatusRaisesException()

    state_machine_thread.start()
    robot_service_thread.start()

    wait_until(
        lambda: States.AwaitNextMission
        in state_machine_thread.state_machine.transitions_list,
        timeout=10,
    )

    scheduling_utilities.start_mission(mission=mission)

    expected_transitions = deque(
        [
            States.UnknownStatus,
            States.AwaitNextMission,
            States.Monitor,
            States.AwaitNextMission,
        ]
    )
    wait_until(
        lambda: state_machine_thread.state_machine.transitions_list
        == expected_transitions
    )
