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
    # TODO: just clear the robot_status_updated event here
    # TODO: this will ensure that we will not get any event updates older than this
    # TODO: in the robot status thread we can even avoid checking status while robot_status_updated is set
    state_machine.events.robot_service_events.robot_status_changed.trigger_event(False)
    return True
