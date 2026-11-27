import logging
import time
from threading import Event

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotActionException,
    RobotException,
    RobotNoMissionRunningException,
)
from robot_interface.models.mission.polygon import Polygon
from robot_interface.robot_interface import RobotInterface


def robot_update_exclusion_polygons(
    signal_exit: Event,
    robot: RobotInterface,
    logger: logging.Logger,
    polygons: list[Polygon],
) -> ErrorMessage | None:
    retries = 0
    error: ErrorMessage | None = None
    while retries < settings.ROBOT_REQUEST_ATTEMPTS_LIMIT:
        if signal_exit.wait(0.01):
            return ErrorMessage(
                ErrorReason.RobotActionException, "Pause thread cancelled"
            )
        try:
            robot.update_exclusion_polygons(polygons)
        except RobotNoMissionRunningException as e:
            return ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
        except (RobotActionException, RobotException) as e:
            logger.warning(
                f"\nFailed to update exclusion polygons because: {e.error_description}"
                f"\nAttempting to update the exclusion polygons again"
            )
            retries += 1
            error = ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
            time.sleep(settings.FSM_SLEEP_TIME)
            continue
        return None

    # error is always set when the loop exits without returning — every iteration
    # either returns early or assigns error before continuing
    assert error is not None
    error_description = (
        f"\nFailed to update exclusion polygons after {retries} attempts because: "
        f"{error.error_description}."
    )

    return ErrorMessage(
        error_reason=error.error_reason,
        error_description=error_description,
    )
