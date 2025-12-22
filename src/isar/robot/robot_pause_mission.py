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


class RobotPauseMissionThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_thread_quitting: Event,
    ):
        self.logger = logging.getLogger("robot")
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.error_message: Optional[ErrorMessage] = None
        Thread.__init__(self, name="Robot pause mission thread")

    def run(self) -> None:
        retries = 0
        error: Optional[ErrorMessage] = None
        while retries < settings.STATE_TRANSITION_NUM_RETIRES:
            if self.signal_thread_quitting.wait(0):
                return
            try:
                self.robot.pause()
            except RobotNoMissionRunningException as e:
                error = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                break
            except (RobotActionException, RobotException) as e:
                self.logger.warning(
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
                self.logger.error(
                    f"\nAn unexpected error occurred while pausing the robot: {str(e)}"
                )
                error = ErrorMessage(
                    error_reason=ErrorReason.RobotUnknownErrorException,
                    error_description=str(e),
                )
                break
            return

        error_description = (
            f"\nFailed to pause the robot after {retries} attempts because: "
            f"{error.error_description}"
            f"\nBe aware that the robot may still be moving even though a pause has "
            "been attempted"
        )

        self.error_message = ErrorMessage(
            error_reason=error.error_reason,
            error_description=error_description,
        )
