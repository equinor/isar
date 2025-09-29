import time
from typing import TYPE_CHECKING

from isar.config.settings import settings
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def is_offline(state_machine: "StateMachine") -> bool:
    robot_status = state_machine.shared_state.robot_status.check()
    return robot_status == RobotStatus.Offline


def is_available_or_home(state_machine: "StateMachine") -> bool:
    robot_status = state_machine.shared_state.robot_status.check()
    return robot_status == RobotStatus.Available or robot_status == RobotStatus.Home


def is_blocked_protective_stop(state_machine: "StateMachine") -> bool:
    robot_status = state_machine.shared_state.robot_status.check()
    return robot_status == RobotStatus.BlockedProtectiveStop


def clear_robot_status(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.clear_robot_status.trigger_event(True)
    start_time: float = time.time()
    while time.time() - start_time < settings.CLEAR_ROBOT_STATUS_TIMEOUT:
        if (
            state_machine.events.robot_service_events.robot_status_cleared.consume_event()
        ):
            return True
        time.sleep(settings.FSM_SLEEP_TIME)
    state_machine.logger.error("Timed out waiting for robot status to be cleared")
    return False
