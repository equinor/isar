import logging
import time
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.communication.queues.events import RobotServiceEvents
from isar.models.communication.queues.queue_utils import trigger_event
from isar.services.utilities.threaded_request import ThreadedRequest
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotCommunicationException,
    RobotCommunicationTimeoutException,
    RobotException,
    RobotTaskStatusException,
)
from robot_interface.models.mission.status import TaskStatus
from robot_interface.robot_interface import RobotInterface


class RobotTaskStatusThread(Thread):
    def __init__(
        self,
        robot_service_events: RobotServiceEvents,
        robot: RobotInterface,
        signal_thread_quitting: Event,
        task_id: str,
    ):
        self.logger = logging.getLogger("robot")
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[ThreadedRequest] = None
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.task_id: str = task_id
        Thread.__init__(self, name="Robot task status thread")

    def run(self) -> None:
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

            trigger_event(self.robot_service_events.task_status_updated, task_status)
            return

        trigger_event(
            self.robot_service_events.task_status_failed,
            failed_task_error,
        )
