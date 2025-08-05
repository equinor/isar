import logging
import time
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.events import RobotServiceEvents
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotActionException,
    RobotException,
)
from robot_interface.robot_interface import RobotInterface


class RobotPauseMissionThread(Thread):
    def __init__(
        self,
        robot_service_events: RobotServiceEvents,
        robot: RobotInterface,
        signal_thread_quitting: Event,
    ):
        self.logger = logging.getLogger("robot")
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        Thread.__init__(self, name="Robot pause mission thread")

    def run(self) -> None:
        retries = 0
        error: Optional[ErrorMessage] = None
        while retries < settings.STATE_TRANSITION_NUM_RETIRES:
            if self.signal_thread_quitting.wait(0):
                return

            try:
                self.robot.pause()
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
            self.robot_service_events.mission_successfully_paused.trigger_event(True)
            return

        error_description = (
            f"\nFailed to pause the robot after {retries} attempts because: "
            f"{error.error_description}"
            f"\nBe aware that the robot may still be moving even though a pause has "
            "been attempted"
        )

        error_message = ErrorMessage(
            error_reason=error.error_reason,
            error_description=error_description,
        )
        self.robot_service_events.mission_failed_to_pause.trigger_event(error_message)
