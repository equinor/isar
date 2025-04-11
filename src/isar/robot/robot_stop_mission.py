import logging
import time
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.communication.queues.events import RobotServiceEvents
from isar.models.communication.queues.queue_utils import (
    trigger_event,
    trigger_event_without_data,
)
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotActionException,
    RobotException,
)
from robot_interface.robot_interface import RobotInterface


class RobotStopMissionThread(Thread):
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
        Thread.__init__(self, name="Robot start mission thread")

    def run(self) -> None:
        retries = 0
        error: Optional[ErrorMessage] = None
        while retries < settings.STOP_ROBOT_ATTEMPTS_LIMIT:
            if self.signal_thread_quitting.wait(0):
                return

            try:
                self.robot.stop()
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

            trigger_event_without_data(
                self.robot_service_events.mission_successfully_stopped
            )
            return

        error_description = (
            f"\nFailed to stop the robot after {retries} attempts because: "
            f"{error.error_description}"
            f"\nBe aware that the robot may still be moving even though a stop has "
            "been attempted"
        )

        error_message = ErrorMessage(
            error_reason=error.error_reason,
            error_description=error_description,
        )

        trigger_event(self.robot_service_events.mission_failed_to_stop, error_message)
