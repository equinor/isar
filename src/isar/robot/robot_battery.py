import logging
import time
from threading import Event as ThreadEvent
from threading import Thread

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event
from robot_interface.models.exceptions.robot_exceptions import RobotException
from robot_interface.robot_interface import RobotInterface


class RobotBatteryThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_exit: ThreadEvent,
        battery_below_mission_threshold_event: Event[EmptyMessage],
        battery_above_recharge_threshold_event: Event[EmptyMessage],
    ):
        self.logger = logging.getLogger("robot")
        self.robot: RobotInterface = robot
        self.signal_exit: ThreadEvent = signal_exit
        self.force_battery_poll_next_iteration: bool = True
        self.battery_below_mission_threshold_event: Event[EmptyMessage] = (
            battery_below_mission_threshold_event
        )
        self.battery_above_recharge_threshold_event: Event[EmptyMessage] = (
            battery_above_recharge_threshold_event
        )
        Thread.__init__(self, name="Robot battery thread")

    def stop(self) -> None:
        return

    def run(self) -> None:
        if self.signal_exit.is_set():
            return

        last_battery_value: float = 100.0

        while not self.signal_exit.wait(0):

            time.sleep(settings.ROBOT_API_BATTERY_POLL_INTERVAL)

            try:
                battery_level = self.robot.get_battery_level()

                if battery_level is None:
                    self.logger.warning(
                        "Received 'None' battery value from robot interface"
                    )
                    continue

                if (
                    battery_level > settings.ROBOT_BATTERY_RECHARGE_THRESHOLD
                    and last_battery_value < settings.ROBOT_BATTERY_RECHARGE_THRESHOLD
                ):
                    self.battery_above_recharge_threshold_event.trigger_event(
                        EmptyMessage()
                    )
                elif (
                    battery_level < settings.ROBOT_BATTERY_RECHARGE_THRESHOLD
                    and last_battery_value > settings.ROBOT_BATTERY_RECHARGE_THRESHOLD
                ):
                    self.battery_above_recharge_threshold_event.clear_event()

                if (
                    battery_level < settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
                    and last_battery_value
                    > settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
                ):
                    self.battery_below_mission_threshold_event.trigger_event(
                        EmptyMessage()
                    )

                elif (
                    battery_level > settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
                    and last_battery_value
                    < settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
                ):
                    self.battery_below_mission_threshold_event.clear_event()

                last_battery_value = battery_level

            except RobotException as e:
                self.logger.error(f"Failed to retrieve robot battery level: {e}")
                continue
            except Exception as e:
                self.logger.error(
                    f"Unhandled exception in robot battery service: {str(e)}"
                )
                continue
        self.logger.info("Exiting robot battery thread")
