import logging
import time
from threading import Event, Thread
from typing import Iterator, Optional

from isar.config.settings import settings
from isar.models.events import RobotServiceEvents
from isar.services.utilities.threaded_request import ThreadedRequest
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotCommunicationException,
    RobotCommunicationTimeoutException,
    RobotException,
    RobotTaskStatusException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import TASKS
from robot_interface.robot_interface import RobotInterface


class RobotMonitorMissionThread(Thread):
    def __init__(
        self,
        robot_service_events: RobotServiceEvents,
        robot: RobotInterface,
        signal_thread_quitting: Event,
        mission: Mission,
    ):
        self.logger = logging.getLogger("robot")
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting

        self.current_mission: Optional[Mission] = mission
        self.task_iterator: Iterator = iter(self.current_mission.tasks)
        self.current_task: Optional[TASKS] = next(self.task_iterator)

        Thread.__init__(self, name="Robot mission monitoring thread")

    def _get_next_task(self):
        try:
            return next(self.task_iterator)
        except StopIteration:
            return None

    def iterate_current_task(self):
        if self.current_task is None:
            raise ValueError("No current task is set")

        if self.current_task.is_finished():
            self.current_task =  self._get_next_task()
            if self.current_task != None:
                self.current_task.status = TaskStatus.InProgress
                self.publish_task_status(task=self.current_task) # TODO:
            self.send_task_status() # TODO:

    def _get_task_status(self):
        task_status: TaskStatus = TaskStatus.NotStarted
        failed_task_error: Optional[ErrorMessage] = None
        request_status_failure_counter: int = 0

        while (
            request_status_failure_counter
            < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
        ):
            if self.signal_thread_quitting.wait(0):
                return
            if request_status_failure_counter > 0:
                time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

            try:
                task_status = self.robot.task_status(self.task_id)
                request_status_failure_counter = 0
            except (
                RobotCommunicationTimeoutException,
                RobotCommunicationException,
            ) as e:
                request_status_failure_counter += 1
                self.logger.error(
                    f"Failed to get task status "
                    f"{request_status_failure_counter} times because: "
                    f"{e.error_description}"
                )

                failed_task_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                continue

            except RobotTaskStatusException as e:
                failed_task_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                break

            except RobotException as e:
                failed_task_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                break

            self.robot_service_events.task_status_updated.trigger_event(task_status)
            return

        self.robot_service_events.task_status_failed.trigger_event(failed_task_error)

    def run(self) -> None:

        self.current_task = self.iterate_current_task()

        while not self.signal_thread_quitting.wait(0):
            
            new_task_status = self._get_task_status()
