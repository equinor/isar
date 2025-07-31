from time import time
from typing import TYPE_CHECKING

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    RobotActionException,
    RobotException,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import ControlMissionResponse
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def stop_mission(state_machine: "StateMachine") -> bool:
    state_machine.logger.info("Stopping mission: %s", state_machine.current_mission.id)

    max_retries = settings.STOP_ROBOT_ATTEMPTS_LIMIT
    retry_interval = settings.STATE_TRANSITION_RETRY_INTERVAL_SEC

    for attempt in range(max_retries):
        try:
            state_machine.robot.stop()
            state_machine.current_mission.status = MissionStatus.Cancelled
            state_machine.current_task.status = TaskStatus.Cancelled

            stopped_mission_response: ControlMissionResponse = (
                state_machine._make_control_mission_response()
            )
            state_machine.events.api_requests.stop_mission.output.put(
                stopped_mission_response
            )

            state_machine.publish_mission_status()
            state_machine.publish_task_status(task=state_machine.current_task)

            state_machine.logger.info("Mission stopped successfully.")
            return True
        except RobotActionException as e:
            state_machine.logger.warning(
                f"Attempt {attempt + 1} to stop mission failed: {e}"
            )
            time.sleep(retry_interval)
        except RobotException as e:
            state_machine.logger.error(
                f"Attempt {attempt + 1} to stop mission raised an RobotException error: {e}"
            )
            time.sleep(retry_interval)
    state_machine.logger.error("Failed to stop mission after multiple attempts.")
    return False


def trigger_stop_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.stop_mission.trigger_event(True)
    return True


def stop_mission_cleanup(state_machine: "StateMachine") -> bool:
    if state_machine.current_mission is None:
        state_machine._queue_empty_response()
        state_machine.reset_state_machine()
        return True

    state_machine.current_mission.status = MissionStatus.Cancelled

    for task in state_machine.current_mission.tasks:
        if task.status in [
            TaskStatus.NotStarted,
            TaskStatus.InProgress,
            TaskStatus.Paused,
        ]:
            task.status = TaskStatus.Cancelled

    stopped_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.stop_mission.output.put(stopped_mission_response)
    state_machine.publish_task_status(task=state_machine.current_task)
    state_machine._finalize()
    return True


def stop_mission_failed(state_machine: "StateMachine") -> bool:
    stopped_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.stop_mission.output.put(stopped_mission_response)
    return True


def stop_return_home_mission_cleanup(state_machine: "StateMachine") -> bool:
    if state_machine.current_mission is None:
        state_machine._queue_empty_response()
        state_machine.reset_state_machine()
        return True

    if not state_machine.events.api_requests.start_mission.input.has_event():
        state_machine.current_mission.status = MissionStatus.Cancelled

        for task in state_machine.current_mission.tasks:
            if task.status in [
                TaskStatus.NotStarted,
                TaskStatus.InProgress,
                TaskStatus.Paused,
            ]:
                task.status = TaskStatus.Cancelled

        stopped_mission_response: ControlMissionResponse = (
            state_machine._make_control_mission_response()
        )
        state_machine.events.api_requests.stop_mission.output.put(
            stopped_mission_response
        )

    state_machine._finalize()
    return True


def stop_return_home_mission_failed(state_machine: "StateMachine") -> bool:
    if state_machine.events.api_requests.start_mission.input.has_event():
        return True
    stopped_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.stop_mission.output.put(stopped_mission_response)
    return True
