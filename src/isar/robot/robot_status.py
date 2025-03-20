import logging
import time
from threading import Event, Thread

from isar.config.settings import settings
from isar.models.communication.queues.events import SharedState
from isar.models.communication.queues.queue_utils import update_shared_state
from robot_interface.models.exceptions.robot_exceptions import RobotException
from robot_interface.robot_interface import RobotInterface


class RobotStatusThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_thread_quitting: Event,
        shared_state: SharedState,
    ):
        self.logger = logging.getLogger("robot")
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.last_robot_status_poll_time: float = (
            time.time() - settings.ROBOT_API_STATUS_POLL_INTERVAL
        )
        Thread.__init__(self, name="Robot status thread")

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
        if self.signal_thread_quitting.is_set():
            return

        while not self.signal_thread_quitting.wait(0.001):
            if not self._is_ready_to_poll_for_status():
                continue
            try:
                robot_status = self.robot.robot_status()

                update_shared_state(self.shared_state.robot_status, robot_status)
                self.last_robot_status_poll_time = time.time()
            except RobotException as e:
                self.logger.error(f"Failed to retrieve robot status: {e}")
                continue
        self.logger.info("Exiting robot status thread")
