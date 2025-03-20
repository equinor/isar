from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotInitializeException,
)
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def put_start_mission_on_queue(state_machine: "StateMachine") -> bool:
    state_machine.events.api_requests.start_mission.output.put(True)
    return True


def initiate_mission(state_machine: "StateMachine") -> bool:
    state_machine.logger.info(
        f"Initialization successful. Starting new mission: "
        f"{state_machine.current_mission.id}"
    )
    state_machine.log_mission_overview(mission=state_machine.current_mission)

    state_machine.current_mission.status = MissionStatus.InProgress
    state_machine.publish_mission_status()
    state_machine.current_task = state_machine.task_selector.next_task()
    state_machine.send_task_status()
    if state_machine.current_task is None:
        return False

    state_machine.current_task.status = TaskStatus.InProgress
    state_machine.publish_task_status(task=state_machine.current_task)
    return True


def initialize_robot(state_machine: "StateMachine") -> bool:
    try:
        state_machine.robot.initialize()
    except (RobotInitializeException, RobotException) as e:
        state_machine.current_task.error_message = ErrorMessage(
            error_reason=e.error_reason, error_description=e.error_description
        )
        state_machine.logger.error(
            f"Failed to initialize robot because: {e.error_description}"
        )
        _initialization_failed(state_machine)
        return False
    return True


def set_mission_to_in_progress(state_machine: "StateMachine") -> bool:
    state_machine.current_mission.status = MissionStatus.InProgress
    state_machine.publish_task_status(task=state_machine.current_task)
    state_machine.logger.info(
        f"Successfully initiated "
        f"{type(state_machine.current_task).__name__} "
        f"task: {str(state_machine.current_task.id)[:8]}"
    )
    return True


def trigger_start_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.start_mission.put(
        state_machine.current_mission
    )
    return True


def _initialization_failed(state_machine: "StateMachine") -> None:
    state_machine.events.api_requests.start_mission.output.put(False)
    state_machine._finalize()
