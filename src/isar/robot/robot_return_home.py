import logging
from threading import Event

from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotAlreadyHomeException,
    RobotException,
    RobotInfeasibleMissionException,
)
from robot_interface.robot_interface import RobotInterface


def robot_return_home(
    signal_exit: Event,
    robot: RobotInterface,
    logger: logging.Logger,
    mission_id: str,
) -> ErrorMessage | None:
    if signal_exit.wait(0.01):
        return ErrorMessage(
            ErrorReason.RobotActionException, "Start mission thread cancelled"
        )
    try:
        robot.initiate_return_home(mission_id)
    except RobotAlreadyHomeException as e:
        logger.info(
            "Robot disregarded return to home mission as its already at home. Return home mission will be assumed successful without running."
        )
        return ErrorMessage(
            error_reason=e.error_reason,
            error_description=e.error_description,
        )
    except RobotInfeasibleMissionException as e:
        logger.error(
            f"Return home is infeasible and cannot be scheduled because: {e.error_description}"
        )
        return ErrorMessage(
            error_reason=e.error_reason,
            error_description=e.error_description,
        )
    except RobotException as e:
        logger.warning(
            f"Initiating return home failed " f"because: {e.error_description}"
        )
        return ErrorMessage(
            error_reason=e.error_reason,
            error_description=e.error_description,
        )
    return None
