from typing import TYPE_CHECKING

from isar.models.communication.queues.queue_utils import check_shared_state
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def is_offline(state_machine: "StateMachine") -> bool:
    robot_status = check_shared_state(state_machine.shared_state.robot_status)
    return robot_status == RobotStatus.Offline


def is_available(state_machine: "StateMachine") -> bool:
    robot_status = check_shared_state(state_machine.shared_state.robot_status)
    return robot_status == RobotStatus.Available


def is_home(state_machine: "StateMachine") -> bool:
    robot_status = check_shared_state(state_machine.shared_state.robot_status)
    return robot_status == RobotStatus.Home


def is_blocked_protective_stop(state_machine: "StateMachine") -> bool:
    robot_status = check_shared_state(state_machine.shared_state.robot_status)
    return robot_status == RobotStatus.BlockedProtectiveStop
