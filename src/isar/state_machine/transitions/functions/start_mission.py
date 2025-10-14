from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import MissionStartResponse
from robot_interface.models.exceptions.robot_exceptions import (
    RobotException,
    RobotInitializeException,
)
from robot_interface.models.mission.status import MissionStatus


def acknowledge_mission(state_machine: "StateMachine") -> bool:
    state_machine.events.api_requests.start_mission.response.trigger_event(
        MissionStartResponse(mission_started=True)
    )
    return True


def prepare_state_machine_before_mission(state_machine: "StateMachine") -> bool:
    state_machine.logger.info(
        "Initiating mission:\n"
        f"  Mission ID: {state_machine.current_mission.id}\n"
        f"  Mission Name: {state_machine.current_mission.name}\n"
        f"  Number of Tasks: {len(state_machine.current_mission.tasks)}"
    )

    state_machine.current_mission.status = MissionStatus.InProgress
    state_machine.publish_mission_status()
    return True


def initialize_robot(state_machine: "StateMachine") -> bool:
    try:
        state_machine.robot.initialize()
    except (RobotInitializeException, RobotException) as e:
        state_machine.logger.error(
            f"Failed to initialize robot because: {e.error_description}"
        )
        _initialization_failed(state_machine)
        return False
    return True


def set_mission_to_in_progress(state_machine: "StateMachine") -> bool:
    state_machine.current_mission.status = MissionStatus.InProgress
    return True


def trigger_start_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.start_mission.trigger_event(
        state_machine.current_mission
    )
    return True


def _initialization_failed(state_machine: "StateMachine") -> None:
    state_machine.events.api_requests.start_mission.response.trigger_event(
        MissionStartResponse(
            mission_started=False,
            mission_not_started_reason="Failed to initialize robot",
        )
    )
    state_machine._finalize()
