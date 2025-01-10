import logging
import queue
import time
from typing import Any, Optional

from injector import inject

from isar.config.settings import settings
from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.queues import Queues
from isar.models.communication.queues.status_queue import StatusQueue
from isar.services.utilities.threaded_request import ThreadedRequest
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotCommunicationException,
    RobotCommunicationTimeoutException,
    RobotException,
    RobotInfeasibleMissionException,
    RobotTaskStatusException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import Task
from robot_interface.robot_interface import RobotInterface


class Robot(object):

    @inject
    def __init__(self, queues: Queues, robot: RobotInterface):
        self.logger = logging.getLogger("robot")
        self.queues: Queues = queues
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[ThreadedRequest] = None
        self.robot_status_thread: Optional[ThreadedRequest] = None
        self.robot_task_status_thread: Optional[ThreadedRequest] = None
        self.last_robot_status_poll_time: float = time.time()
        self.current_status = Optional[None]
        self.request_status_failure_counter: int = 0
        self.request_status_failure_counter_limit: int = (
            settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
        )

    def _trigger_event(self, queueio: QueueIO, data: Any = None) -> Any:
        queueio.input.put(data if data is not None else True)

    def _check_shared_state(self, queueio: StatusQueue):
        try:
            return queueio.check()
        except queue.Empty:
            return None

    def _check_for_event(self, queueio: QueueIO) -> Any:
        try:
            return queueio.input.get(block=False)
        except queue.Empty:
            return None

    def run_robot_status_thread(self):
        while True:
            robot_status = self.robot.robot_status()
            if (
                robot_status != self.current_status
                and robot_status == RobotStatus.Offline
            ):
                self._trigger_event(self.queues.robot_offline)
            if (
                robot_status != self.current_status
                and robot_status != RobotStatus.Offline
            ):
                self._trigger_event(self.queues.robot_online)
            self.current_status = robot_status
            time.sleep(settings.FSM_SLEEP_TIME)

    def run_robot_task_status_thread(self):
        while True:
            current_state: Optional[States] = self._check_shared_state(
                self.queues.state
            )

            if current_state not in [States.Monitor, States.Paused, States.Stop]:
                # Here we exit the thread as the mission is done
                break

            current_task: Optional[Task] = self._check_shared_state(
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
                    time.sleep(settings.FSM_SLEEP_TIME)
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
                self._trigger_event(
                    self.queues.robot_task_status_failed,
                    failed_task_error,
                )
                task_status = TaskStatus.Failed
            else:
                self._trigger_event(self.queues.robot_task_status, task_status)
            self.current_status = task_status
            time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

    def stop(self) -> None:
        if self.robot_status_thread:
            self.robot_status_thread.wait_for_thread()
        if self.robot_task_status_thread:
            self.robot_task_status_thread.wait_for_thread()
        if self.start_mission_thread:
            self.start_mission_thread.wait_for_thread()
        self.robot_status_thread = None
        self.robot_task_status_thread = None
        self.start_mission_thread = None

    def run_start_mission_thread(self, mission_or_task: Mission | Task):
        retries = 0
        started_mission = False
        try:
            while not started_mission:
                try:
                    self.robot.initiate_mission(mission_or_task)
                except RobotException as e:
                    retries += 1
                    self.logger.warning(
                        f"Initiating failed #: {str(retries)} "
                        f"because: {e.error_description}"
                    )

                    if retries >= settings.INITIATE_FAILURE_COUNTER_LIMIT:
                        error_description = (
                            f"Mission will be cancelled after failing to initiate "
                            f"{settings.INITIATE_FAILURE_COUNTER_LIMIT} times because: "
                            f"{e.error_description}"
                        )

                        self._trigger_event(
                            self.queues.robot_mission_failed,
                            ErrorMessage(
                                error_reason=e.error_reason,
                                error_description=error_description,
                            ),
                        )
                started_mission = True
        except RobotInfeasibleMissionException as e:
            self._trigger_event(
                self.queues.robot_mission_failed,
                ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                ),
            )
        self.robot_task_status_thread = ThreadedRequest(
            request_func=self.run_robot_task_status_thread
        )
        self.robot_task_status_thread.start_thread(name="Robot task status thread")

    def run(self) -> None:
        self.robot_status_thread = ThreadedRequest(
            request_func=self.run_robot_status_thread
        )
        self.robot_status_thread.start_thread(name="Robot status thread")
        while True:
            start_mission_or_task = self._check_for_event(
                self.queues.state_machine_start_mission
            )
            if start_mission_or_task is not None:
                if (
                    self.start_mission_thread is not None
                    and self.start_mission_thread._is_thread_alive()
                ):
                    self.start_mission_thread.wait_for_thread()
                self.start_mission_thread = ThreadedRequest(
                    request_func=self.run_start_mission_thread,
                )
                self.start_mission_thread.start_thread(
                    start_mission_or_task, name="Robot start mission thread"
                )
