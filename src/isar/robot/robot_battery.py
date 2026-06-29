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
        signal_exit: Event,
        shared_state: SharedState,
    ):
        self.logger = logging.getLogger("robot")
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.signal_exit: Event = signal_exit
        self.last_robot_battery_poll_time: float = time.time()
        self.force_battery_poll_next_iteration: bool = True
        Thread.__init__(self, name="Robot battery thread")

    def stop(self) -> None:
        return

    def run(self) -> None:
        if self.signal_exit.is_set():
            return

        while not self.signal_exit.wait(0):

            time.sleep(settings.ROBOT_API_BATTERY_POLL_INTERVAL)

            try:
                self.last_robot_battery_poll_time = time.time()

                robot_battery_level = self.robot.get_battery_level()

                self.shared_state.robot_battery_level.update(robot_battery_level)

            except RobotException as e:
                self.logger.error(f"Failed to retrieve robot battery level: {e}")
                continue
            except Exception as e:
                self.logger.error(
                    f"Unhandled exception in robot battery service: {str(e)}"
                )
                continue
        self.logger.info("Exiting robot battery thread")
