from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

import time

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    RobotActionException,
    RobotException,
    RobotNoMissionRunningException,
)


def resume_mission(state_machine: "StateMachine") -> bool:
    state_machine.logger.info("Resuming mission")

    max_retries = settings.STATE_TRANSITION_NUM_RETIRES
    retry_interval = settings.STATE_TRANSITION_RETRY_INTERVAL_SEC

    for attempt in range(max_retries):
        try:
            state_machine.robot.resume()

            resume_mission_response: ControlMissionResponse = ControlMissionResponse(
                success=True
            )
            state_machine.events.api_requests.resume_mission.response.trigger_event(
                resume_mission_response
            )

            state_machine.logger.info("Mission resumed successfully.")
            return True
        except RobotNoMissionRunningException as e:
            state_machine.logger.error(
                f"Failed to resume mission: {e.error_reason}. {e.error_description}"
            )
            # TODO: this will make it go to paused, instead of awaitnextmission
            return False
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
