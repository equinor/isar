import time
from collections import deque

from isar.robot.robot_status import RobotStatusThread
from isar.state_machine.states_enum import States
from tests.test_mocks.robot_interface import StubRobotBlockedProtectiveStopToHomeTest
from tests.test_mocks.state_machine_mocks import (
    RobotServiceThreadMock,
    StateMachineThreadMock,
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
    time.sleep(5)

    assert state_machine_thread.state_machine.transitions_list == deque(
        [States.UnknownStatus, States.BlockedProtectiveStop, States.Home]
    )
