import logging
import time
from threading import Event, Thread

from isar.config.settings import settings
from isar.models.events import SharedState
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

        thread_check_interval = settings.THREAD_CHECK_INTERVAL

        while not self.signal_thread_quitting.wait(thread_check_interval):
            if not self._is_ready_to_poll_for_status():
                continue
            try:
                self.last_robot_status_poll_time = time.time()

                robot_status = self.robot.robot_status()
                robot_battery_level = self.robot.get_battery_level()

                self.shared_state.robot_status.update(robot_status)
                self.shared_state.robot_battery_level.update(robot_battery_level)
            except RobotException as e:
                self.logger.error(f"Failed to retrieve robot status: {e}")
                continue
        self.logger.info("Exiting robot status thread")
