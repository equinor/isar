import logging
import time
from threading import Event, Thread

from isar.config.settings import settings
from isar.models.events import SharedState
from robot_interface.models.exceptions.robot_exceptions import RobotException
from robot_interface.robot_interface import RobotInterface


class RobotBatteryThread(Thread):
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
        self.last_robot_battery_poll_time: float = time.time()
        self.force_battery_poll_next_iteration: bool = True
        Thread.__init__(self, name="Robot battery thread")

    def stop(self) -> None:
        return

    def _is_ready_to_poll_for_battery(self) -> bool:
        if self.force_battery_poll_next_iteration:
            self.force_battery_poll_next_iteration = False
            return True

        time_since_last_robot_battery_poll = (
            time.time() - self.last_robot_battery_poll_time
        )
        return (
            time_since_last_robot_battery_poll
            > settings.ROBOT_API_BATTERY_POLL_INTERVAL
        )

    def run(self):
        if self.signal_thread_quitting.is_set():
            return

        thread_check_interval = settings.THREAD_CHECK_INTERVAL

        while not self.signal_thread_quitting.wait(thread_check_interval):
            if not self._is_ready_to_poll_for_battery():
                continue
            try:
                self.last_robot_battery_poll_time = time.time()

                robot_battery_level = self.robot.get_battery_level()

                self.shared_state.robot_battery_level.update(robot_battery_level)
            except RobotException as e:
                self.logger.error(f"Failed to retrieve robot battery level: {e}")
                continue
        self.logger.info("Exiting robot battery thread")
