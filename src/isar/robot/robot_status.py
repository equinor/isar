import logging
import time
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.communication.queues.queue_utils import trigger_event
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.threaded_request import ThreadedRequest
from robot_interface.models.mission.status import RobotStatus
from robot_interface.robot_interface import RobotInterface


class RobotStatusThread(Thread):

    def __init__(
        self, queues: Queues, robot: RobotInterface, signal_thread_quitting: Event
    ):
        self.logger = logging.getLogger("robot")
        self.queues: Queues = queues
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[ThreadedRequest] = None
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.current_status: Optional[RobotStatus] = None
        Thread.__init__(self, name="Robot status thread")

    def run(self):
        while True:
            if self.signal_thread_quitting.is_set():
                break
            robot_status = self.robot.robot_status()
            if (
                robot_status != self.current_status
                and robot_status == RobotStatus.Offline
            ):
                trigger_event(self.queues.robot_offline)
            if (
                robot_status != self.current_status
                and robot_status != RobotStatus.Offline
            ):
                trigger_event(self.queues.robot_online)
            self.current_status = robot_status
            time.sleep(settings.FSM_SLEEP_TIME)
        self.logger.info("Exiting robot status thread")
