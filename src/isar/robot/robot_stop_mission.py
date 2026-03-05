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


def robot_stop_mission(
    signal_exit: Event, robot: RobotInterface, logger: logging.Logger
) -> ErrorMessage | None:
    retries = 0
    error: Optional[ErrorMessage] = None
    while retries < settings.STOP_ROBOT_ATTEMPTS_LIMIT:
        if signal_exit.wait(0):
            error_message = ErrorMessage(
                error_reason=ErrorReason.RobotUnknownErrorException,
                error_description="Stop mission thread cancelled",
            )
            return error_message

        try:
            robot.stop()
        except RobotNoMissionRunningException:
            return None  # This is considered a success
        except (RobotActionException, RobotException) as e:
            logger.warning(
                f"\nFailed to stop robot because: {e.error_description}"
                f"\nAttempting to stop the robot again"
            )
            retries += 1
            error = ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
            time.sleep(settings.FSM_SLEEP_TIME)
            continue
        except Exception as e:
            logger.error(f"Unhandled exception in robot stop mission service: {str(e)}")
            return ErrorMessage(
                error_reason=ErrorReason.RobotUnknownErrorException,
                error_description=str(e),
            )
        return None

    assert error is not None
    error_description = (
        f"\nFailed to stop the robot after {retries} attempts because: "
        f"{error.error_description}"
        f"\nBe aware that the robot may still be moving even though a stop has "
        "been attempted"
    )

    return ErrorMessage(
        error_reason=error.error_reason,
        error_description=error_description,
    )
