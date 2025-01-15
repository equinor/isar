import logging
import time
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.communication.queues.queues import Queues
from isar.models.communication.queues.queue_utils import (
    check_shared_state,
    trigger_event,
)
from isar.services.utilities.threaded_request import ThreadedRequest
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotCommunicationException,
    RobotCommunicationTimeoutException,
    RobotException,
    RobotTaskStatusException,
)
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import Task
from robot_interface.robot_interface import RobotInterface


class RobotTaskStatusThread(Thread):

    def __init__(
        self, queues: Queues, robot: RobotInterface, signal_thread_quitting: Event
    ):
        self.logger = logging.getLogger("robot")
        self.queues: Queues = queues
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[ThreadedRequest] = None
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.current_status: Optional[TaskStatus] = None
        self.request_status_failure_counter: int = 0
        self.request_status_failure_counter_limit: int = (
            settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
        )
        Thread.__init__(self, name="Robot task status thread")

    def run(self):
        while True:
            if self.signal_thread_quitting.is_set():
                break
            current_state: Optional[States] = check_shared_state(self.queues.state)

            if current_state not in [States.Monitor, States.Paused, States.Stop]:
                time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)
                continue

            current_task: Optional[Task] = check_shared_state(
                self.queues.state_machine_current_task
            )

            failed_task_error: Optional[ErrorMessage] = None

            if current_task is None:
                continue

            task_status: TaskStatus
            try:
                task_status = self.robot.task_status(current_task.id)
                self.request_status_failure_counter = 0
            except (
                RobotCommunicationTimeoutException,
                RobotCommunicationException,
            ) as e:
                self.request_status_failure_counter += 1

                if (
                    self.request_status_failure_counter
                    >= self.request_status_failure_counter_limit
                ):
                    self.logger.error(
                        f"Failed to get task status "
                        f"{self.request_status_failure_counter} times because: "
                        f"{e.error_description}"
                    )
                    self.logger.error(
                        f"Monitoring task failed because: {e.error_description}"
                    )
                    failed_task_error = ErrorMessage(
                        error_reason=e.error_reason,
                        error_description=e.error_description,
                    )

                else:
                    time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)
                    continue

            except RobotTaskStatusException as e:
                failed_task_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )

            except RobotException as e:
                failed_task_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )

            if failed_task_error is not None:
                trigger_event(
                    self.queues.robot_task_status_failed,
                    failed_task_error,
                )
                task_status = TaskStatus.Failed
            else:
                trigger_event(self.queues.robot_task_status, task_status)
            self.current_status = task_status
            time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)
        self.logger.info("Exiting robot task status thread")
