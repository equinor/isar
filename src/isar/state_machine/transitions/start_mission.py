from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotInfeasibleMissionException,
    RobotInitializeException,
)
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def put_start_mission_on_queue(state_machine: "StateMachine") -> bool:
    state_machine.queues.start_mission.output.put(True)
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


def try_initiate_task_or_mission(state_machine: "StateMachine") -> bool:
    retries = 0
    started_mission = False
    try:
        while not started_mission:
            try:
                state_machine.robot.initiate_mission(state_machine.current_mission)
            except RobotException as e:
                retries += 1
                state_machine.logger.warning(
                    f"Initiating failed #: {str(retries)} "
                    f"because: {e.error_description}"
                )

                if retries >= settings.INITIATE_FAILURE_COUNTER_LIMIT:
                    state_machine.current_task.error_message = ErrorMessage(
                        error_reason=e.error_reason,
                        error_description=e.error_description,
                    )
                    state_machine.logger.error(
                        f"Mission will be cancelled after failing to initiate "
                        f"{settings.INITIATE_FAILURE_COUNTER_LIMIT} times because: "
                        f"{e.error_description}"
                    )
                    _initiate_failed(state_machine)
                    return False
            started_mission = True
    except RobotInfeasibleMissionException as e:
        state_machine.current_mission.error_message = ErrorMessage(
            error_reason=e.error_reason, error_description=e.error_description
        )
        state_machine.logger.warning(
            f"Failed to initiate mission "
            f"{str(state_machine.current_mission.id)[:8]} because: "
            f"{e.error_description}"
        )
        _initiate_failed(state_machine)
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


def _initialization_failed(state_machine: "StateMachine") -> None:
    state_machine.queues.start_mission.output.put(False)
    state_machine._finalize()


def _initiate_failed(state_machine: "StateMachine") -> None:
    state_machine.current_task.status = TaskStatus.Failed
    state_machine.current_mission.status = MissionStatus.Failed
    state_machine.publish_task_status(task=state_machine.current_task)
    state_machine._finalize()
