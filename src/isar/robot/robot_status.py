import logging
import time
from threading import Event, Thread

from isar.config.settings import settings
from isar.models.communication.queues.queue_utils import update_shared_state
from isar.models.communication.queues.queues import Queues
from robot_interface.robot_interface import RobotInterface


class RobotStatusThread(Thread):

    def __init__(
        self, queues: Queues, robot: RobotInterface, signal_thread_quitting: Event
    ):
        self.logger = logging.getLogger("robot")
        self.queues: Queues = queues
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.last_robot_status_poll_time: float = time.time()
        Thread.__init__(self, name="Robot status thread", daemon=True)

    def stop(self) -> None:
        return

    def _is_ready_to_poll_for_status(self) -> bool:
        time_since_last_robot_status_poll = (
            time.time() - self.last_robot_status_poll_time
        )
        return (
            time_since_last_robot_status_poll > settings.ROBOT_API_STATUS_POLL_INTERVAL
        )

    def run(self):
        while True:
            if self.signal_thread_quitting.is_set():
                break

            if not self._is_ready_to_poll_for_status():
                continue

            robot_status = self.robot.robot_status()

            update_shared_state(self.queues.robot_status, robot_status)
            self.last_robot_status_poll_time = time.time()
        self.logger.info("Exiting robot status thread")
