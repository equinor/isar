import logging
import time
from threading import Event, Thread
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


class RobotStopMissionThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_thread_quitting: Event,
    ):
        self.logger = logging.getLogger("robot")
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.error_message: Optional[ErrorMessage] = None
        Thread.__init__(self, name="Robot stop mission thread")

    def run(self) -> None:
        retries = 0
        error: Optional[ErrorMessage] = None
        while retries < settings.STOP_ROBOT_ATTEMPTS_LIMIT:
            if self.signal_thread_quitting.wait(0):
                self.error_message = ErrorMessage(
                    error_reason=ErrorReason.RobotUnknownErrorException,
                    error_description="Stop mission thread cancelled",
                )
                return

            try:
                self.robot.stop()
            except RobotNoMissionRunningException:
                return
            except (RobotActionException, RobotException) as e:
                self.logger.warning(
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
                self.logger.error(
                    f"Unhandled exception in robot stop mission service: {str(e)}"
                )
                error = ErrorMessage(
                    error_reason=ErrorReason.RobotUnknownErrorException,
                    error_description=str(e),
                )
            return

        error_description = (
            f"\nFailed to stop the robot after {retries} attempts because: "
            f"{error.error_description}"
            f"\nBe aware that the robot may still be moving even though a stop has "
            "been attempted"
        )

        self.error_message = ErrorMessage(
            error_reason=error.error_reason,
            error_description=error_description,
        )
