import logging
from threading import Event

from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotAlreadyHomeException,
    RobotException,
    RobotInfeasibleMissionException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.robot_interface import RobotInterface


def robot_start_mission(
    signal_exit: Event,
    robot: RobotInterface,
    logger: logging.Logger,
    mission: Mission,
) -> ErrorMessage | None:
    if signal_exit.wait(0):
        return ErrorMessage(
            ErrorReason.RobotActionException, "Start mission thread cancelled"
        )
    try:
        robot.initiate_mission(mission)
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
            f"Mission is infeasible and cannot be scheduled because: {e.error_description}"
        )
        return ErrorMessage(
            error_reason=e.error_reason,
            error_description=e.error_description,
        )
    except RobotException as e:
        logger.warning(f"Initiating mission failed " f"because: {e.error_description}")
        return ErrorMessage(
            error_reason=e.error_reason,
            error_description=e.error_description,
        )
    except Exception as e:
        logger.warning(f"Initiating mission failed due to unknown exception: {e}")
        return ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description=str(e),
        )
    return None
