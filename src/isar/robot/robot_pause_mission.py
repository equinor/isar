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


def robot_pause_mission(
    signal_exit: Event, robot: RobotInterface, logger: logging.Logger
) -> ErrorMessage | None:
    retries = 0
    error: Optional[ErrorMessage] = None
    while retries < settings.STATE_TRANSITION_NUM_RETIRES:
        if signal_exit.wait(0):
            return ErrorMessage(
                ErrorReason.RobotActionException, "Pause thread cancelled"
            )
        try:
            robot.pause()
        except RobotNoMissionRunningException as e:
            return ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
        except (RobotActionException, RobotException) as e:
            logger.warning(
                f"\nFailed to pause robot because: {e.error_description}"
                f"\nAttempting to pause the robot again"
            )
            retries += 1
            error = ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
            time.sleep(settings.FSM_SLEEP_TIME)
            continue
        except Exception as e:
            logger.error(
                f"\nAn unexpected error occurred while pausing the robot: {str(e)}"
            )
            return ErrorMessage(
                error_reason=ErrorReason.RobotUnknownErrorException,
                error_description=str(e),
            )
        return None

    assert error is not None
    error_description = (
        f"\nFailed to pause the robot after {retries} attempts because: "
        f"{error.error_description}"
        f"\nBe aware that the robot may still be moving even though a pause has "
        "been attempted"
    )

    return ErrorMessage(
        error_reason=error.error_reason,
        error_description=error_description,
    )
