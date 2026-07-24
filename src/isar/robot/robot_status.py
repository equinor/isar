import logging
import time
from threading import Event, Thread

from isar.config.settings import settings
from isar.models.events import RobotServiceEvents, StateMachineEvents
from robot_interface.models.exceptions.robot_exceptions import RobotException
from robot_interface.robot_interface import RobotInterface


class RobotStatusThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_exit: Event,
        robot_service_events: RobotServiceEvents,
        state_machine_events: StateMachineEvents,
    ):
        self.logger = logging.getLogger("robot")
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.state_machine_events: StateMachineEvents = state_machine_events
        self.robot: RobotInterface = robot
        self.signal_exit: Event = signal_exit
        self.robot_status_poll_interval: float = settings.ROBOT_API_STATUS_POLL_INTERVAL
        self.last_robot_status_poll_time: float = time.time()
        Thread.__init__(self, name="Robot status thread")

    def stop(self) -> None:
        return

    def run(self) -> None:
        if self.signal_exit.is_set():
            return

        while not self.signal_exit.wait(0):

            time.sleep(settings.ROBOT_API_STATUS_POLL_INTERVAL)

            try:
                self.last_robot_status_poll_time = time.time()

                robot_status = self.robot.robot_status()

                if (
                    robot_status
                    and robot_status
                    is not self.robot_service_events.robot_status_update.check()
                ):
                    self.robot_service_events.robot_status_update.clear_event()
                    self.robot_service_events.robot_status_update.trigger_event(
                        robot_status
                    )
            except RobotException as e:
                self.logger.error(f"Failed to retrieve robot status: {e}")
                continue
            except Exception as e:
                self.logger.error(
                    f"Unhandled exception in robot status service: {str(e)}"
                )
                continue
        self.logger.info("Exiting robot status thread")
