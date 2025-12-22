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


class RobotResumeMissionThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_thread_quitting: Event,
    ):
        self.logger = logging.getLogger("robot")
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.error_message: Optional[ErrorMessage] = None
        Thread.__init__(self, name="Robot resume mission thread")

    def run(self) -> None:
        retries = 0
        error: Optional[ErrorMessage] = None
        while retries < settings.STATE_TRANSITION_NUM_RETIRES:
            if self.signal_thread_quitting.wait(0):
                return
            try:
                self.robot.resume()
                return
            except (RobotActionException, RobotException) as e:
                self.logger.warning(
                    f"Attempt {retries + 1} to resume mission failed: {e.error_description}"
                    f"\nAttempting to resume the robot again"
                )
                error = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                time.sleep(settings.FSM_SLEEP_TIME)
                retries += 1
                continue
            except RobotNoMissionRunningException as e:
                self.logger.error(
                    f"Failed to resume mission: {e.error_reason}. {e.error_description}"
                )
                error = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                break
            except Exception as e:
                self.logger.error(
                    f"Unhandled exception in robot resume mission service: {str(e)}"
                )
                error = ErrorMessage(
                    error_reason=ErrorReason.RobotUnknownErrorException,
                    error_description=str(e),
                )
                break

        error_description = (
            f"\nFailed to resume the robot after {retries + 1} attempts because: "
            f"{error.error_description}"
            f"\nBe aware that the robot may still be moving even though a resume has "
            "been attempted"
        )

        self.error_message = ErrorMessage(
            error_reason=error.error_reason,
            error_description=error_description,
        )
