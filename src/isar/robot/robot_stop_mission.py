import logging
import time
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.communication.queues.events import Events
from isar.models.communication.queues.queue_utils import trigger_event
from robot_interface.models.exceptions.robot_exceptions import (
    RobotActionException,
    RobotException,
)
from robot_interface.robot_interface import RobotInterface


class RobotStopMissionThread(Thread):

    def __init__(
        self,
        events: Events,
        robot: RobotInterface,
        signal_thread_quitting: Event,
    ):
        self.logger = logging.getLogger("robot")
        self.events: Events = events
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        Thread.__init__(self, name="Robot start mission thread")

    def run(self) -> None:
        retries = 0
        error_description: Optional[str] = None
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
                error_description = e.error_description
                time.sleep(settings.FSM_SLEEP_TIME)
                continue

            trigger_event(self.events.robot_service_events.mission_successfully_stopped)
            return

        error_message = (
            f"\nFailed to stop the robot after {retries} attempts because: "
            f"{error_description}"
            f"\nBe aware that the robot may still be moving even though a stop has "
            "been attempted"
        )

        trigger_event(
            self.events.robot_service_events.mission_failed_to_stop, error_message
        )
