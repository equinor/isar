from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

import time

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    RobotActionException,
    RobotException,
)
from robot_interface.models.mission.status import MissionStatus, TaskStatus


def resume_mission(state_machine: "StateMachine") -> bool:
    state_machine.logger.info("Resuming mission: %s", state_machine.current_mission.id)

    max_retries = settings.STATE_TRANSITION_NUM_RETIRES
    retry_interval = settings.STATE_TRANSITION_RETRY_INTERVAL_SEC

    for attempt in range(max_retries):
        try:
            state_machine.robot.resume()
            state_machine.current_mission.status = MissionStatus.InProgress
            state_machine.current_mission.error_message = None
            state_machine.current_task.status = TaskStatus.InProgress

            state_machine.mission_ongoing = True

            state_machine.publish_mission_status()
            state_machine.publish_task_status(task=state_machine.current_task)

            resume_mission_response: ControlMissionResponse = (
                state_machine._make_control_mission_response()
            )
            state_machine.events.api_requests.resume_mission.response.put(
                resume_mission_response
            )

            state_machine.logger.info("Mission resumed successfully.")
            return True
        except RobotActionException as e:
            state_machine.logger.warning(
                f"Attempt {attempt + 1} to resume mission failed: {e.error_description}"
            )
            time.sleep(retry_interval)
        except RobotException as e:
            state_machine.logger.warning(
                f"Attempt {attempt + 1} to resume mission raised a RobotException: {e.error_description}"
            )
            time.sleep(retry_interval)

    state_machine.logger.error("Failed to resume mission after multiple attempts.")
    return False
