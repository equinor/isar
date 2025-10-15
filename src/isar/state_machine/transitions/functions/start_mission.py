from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import MissionStartResponse
from robot_interface.models.exceptions.robot_exceptions import (
    RobotException,
    RobotInitializeException,
)


def acknowledge_mission(state_machine: "StateMachine") -> bool:
    state_machine.events.api_requests.start_mission.response.trigger_event(
        MissionStartResponse(mission_started=True)
    )
    return True


def initialize_robot(state_machine: "StateMachine") -> bool:
    try:
        state_machine.robot.initialize()
    except (RobotInitializeException, RobotException) as e:
        state_machine.logger.error(
            f"Failed to initialize robot because: {e.error_description}"
        )
        _initialization_failed(state_machine)
        state_machine.print_transitions()
        return False
    return True


def _initialization_failed(state_machine: "StateMachine") -> None:
    state_machine.events.api_requests.start_mission.response.trigger_event(
        MissionStartResponse(
            mission_started=False,
            mission_not_started_reason="Failed to initialize robot",
        )
    )
    state_machine.print_transitions()
