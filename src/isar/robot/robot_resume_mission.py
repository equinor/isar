import logging
import time
from threading import Event
from typing import Optional

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotActionException,
    RobotException,
    RobotNoMissionRunningException,
)
from robot_interface.robot_interface import RobotInterface


def robot_resume_mission(
    signal_exit: Event, robot: RobotInterface, logger: logging.Logger
) -> ErrorMessage | None:
    retries = 0
    error: Optional[ErrorMessage] = None
    while retries < settings.STATE_TRANSITION_NUM_RETIRES:
        if signal_exit.wait(0):
            return ErrorMessage(
                ErrorReason.RobotActionException, "Resume thread cancelled"
            )
        try:
            robot.resume()
            return None
        except RobotNoMissionRunningException as e:
            logger.error(
                f"Failed to resume mission: {e.error_reason}. {e.error_description}"
            )
            return ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
        except (RobotActionException, RobotException) as e:
            logger.warning(
                f"Attempt {retries + 1} to resume mission failed: {e.error_description}"
                f"\nAttempting to resume the robot again"
            )
            error = ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
            time.sleep(settings.FSM_SLEEP_TIME)
            retries += 1
            continue
        except Exception as e:
            logger.error(
                f"Unhandled exception in robot resume mission service: {str(e)}"
            )
            return ErrorMessage(
                error_reason=ErrorReason.RobotUnknownErrorException,
                error_description=str(e),
            )

    assert error is not None
    error_description = (
        f"\nFailed to resume the robot after {retries + 1} attempts because: "
        f"{error.error_description}"
        f"\nBe aware that the robot may still be moving even though a resume has "
        "been attempted"
    )

    return ErrorMessage(
        error_reason=error.error_reason,
        error_description=error_description,
    )
