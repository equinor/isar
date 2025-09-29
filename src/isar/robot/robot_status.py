import logging
import time
from threading import Event, Thread

from isar.config.settings import settings
from isar.models.events import RobotServiceEvents, SharedState, StateMachineEvents
from robot_interface.models.exceptions.robot_exceptions import RobotException
from robot_interface.robot_interface import RobotInterface


class RobotStatusThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_thread_quitting: Event,
        shared_state: SharedState,
        robot_service_events: RobotServiceEvents,
        state_machine_events: StateMachineEvents,
    ):
        self.logger = logging.getLogger("robot")
        self.shared_state: SharedState = shared_state
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.state_machine_events: StateMachineEvents = state_machine_events
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.robot_status_poll_interval: float = settings.ROBOT_API_STATUS_POLL_INTERVAL
        self.last_robot_status_poll_time: float = time.time()
        self.force_status_poll_next_iteration: bool = True
        Thread.__init__(self, name="Robot status thread")

    def stop(self) -> None:
        return

    def _is_ready_to_poll_for_status(self) -> bool:
        if self.force_status_poll_next_iteration:
            self.force_status_poll_next_iteration = False
            return True

        time_since_last_robot_status_poll = (
            time.time() - self.last_robot_status_poll_time
        )
        return time_since_last_robot_status_poll > self.robot_status_poll_interval

    def run(self):
        if self.signal_thread_quitting.is_set():
            return

        thread_check_interval = settings.THREAD_CHECK_INTERVAL

        while not self.signal_thread_quitting.wait(thread_check_interval):
            if self.state_machine_events.clear_robot_status.consume_event() is not None:
                self.shared_state.robot_status.clear_event()
                self.robot_service_events.robot_status_changed.clear_event()
                self.robot_service_events.robot_status_cleared.trigger_event(True)
                self.force_status_poll_next_iteration = True

            if not self._is_ready_to_poll_for_status():
                continue

            try:
                self.last_robot_status_poll_time = time.time()

                robot_status = self.robot.robot_status()

                if robot_status is not self.shared_state.robot_status.check():
                    self.shared_state.robot_status.update(robot_status)
                    self.robot_service_events.robot_status_changed.trigger_event(True)
            except RobotException as e:
                self.logger.error(f"Failed to retrieve robot status: {e}")
                continue
        self.logger.info("Exiting robot status thread")
