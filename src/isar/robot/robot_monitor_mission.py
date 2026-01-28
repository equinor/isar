import logging
import time
from threading import Event, Thread
from typing import Callable, Iterator, Optional

from isar.config.settings import settings
from isar.services.utilities.mqtt_utilities import (
    publish_mission_status,
    publish_task_status,
)
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotCommunicationException,
    RobotCommunicationTimeoutException,
    RobotException,
    RobotMissionStatusException,
    RobotTaskStatusException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import TASKS, InspectionTask
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface


def get_next_task(task_iterator: Iterator[TASKS]) -> Optional[TASKS]:
    try:
        return next(task_iterator)
    except StopIteration:
        return None


def is_finished(task_status: TaskStatus) -> bool:
    if (
        task_status == TaskStatus.Successful
        or task_status == TaskStatus.PartiallySuccessful
        or task_status == TaskStatus.Cancelled
        or task_status == TaskStatus.Failed
    ):
        return True
    return False


def should_upload_inspections(task: TASKS) -> bool:
    if settings.UPLOAD_INSPECTIONS_ASYNC:
        return False

    return task.status == TaskStatus.Successful and isinstance(task, InspectionTask)


class RobotMonitorMissionThread(Thread):
    def __init__(
        self,
        request_inspection_upload: Callable[[TASKS], None],
        robot: RobotInterface,
        mqtt_publisher: MqttClientInterface,
        signal_thread_quitting: Event,
        signal_mission_stopped: Event,
        mission: Mission,
    ):
        self.logger = logging.getLogger("robot")
        self.request_inspection_upload: Callable[[TASKS], None] = (
            request_inspection_upload
        )
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.signal_mission_stopped: Event = signal_mission_stopped
        self.mqtt_publisher = mqtt_publisher
        self.mission_id: str = mission.id
        self.tasks = mission.tasks

        self.error_message: Optional[ErrorMessage] = None

        Thread.__init__(self, name="Robot mission monitoring thread")

    def _get_task_status(self, task_id: str) -> TaskStatus:
        task_status: TaskStatus = TaskStatus.NotStarted
        failed_task_error: Optional[ErrorMessage] = None
        request_status_failure_counter: int = 0

        while (
            request_status_failure_counter
            < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
        ):
            if self.signal_thread_quitting.wait(0) or self.signal_mission_stopped.wait(
                0
            ):
                failed_task_error = ErrorMessage(
                    error_reason=ErrorReason.RobotTaskStatusException,
                    error_description="Task status collection was cancelled by monitor thread exit",
                )
                break
            if request_status_failure_counter > 0:
                time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

            try:
                task_status = self.robot.task_status(task_id)
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

            except RobotException as e:
                failed_task_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                break

            except Exception as e:
                failed_task_error = ErrorMessage(
                    error_reason=ErrorReason.RobotUnknownErrorException,
                    error_description=str(e),
                )
                break

            return task_status

        raise RobotTaskStatusException(
            error_description=failed_task_error.error_description
        )

    def _get_mission_status(self, mission_id: str) -> MissionStatus:
        mission_status: MissionStatus = MissionStatus.NotStarted
        failed_mission_error: Optional[ErrorMessage] = None
        request_status_failure_counter: int = 0

        while (
            request_status_failure_counter
            < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
        ):
            if self.signal_thread_quitting.wait(0) or self.signal_mission_stopped.wait(
                0
            ):
                break
            if request_status_failure_counter > 0:
                time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

            try:
                mission_status = self.robot.mission_status(mission_id)
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

                failed_mission_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                continue

            except RobotException as e:
                failed_mission_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                break

            except Exception as e:
                failed_mission_error = ErrorMessage(
                    error_reason=ErrorReason.RobotUnknownErrorException,
                    error_description=str(e),
                )
                break

            return mission_status

        raise RobotMissionStatusException(
            error_description=(
                failed_mission_error.error_description
                if failed_mission_error
                else "Mission status thread cancelled"
            )
        )

    def _log_task_status(self, task: TASKS) -> None:
        if task.status == TaskStatus.Failed:
            self.logger.warning(
                f"Task: {str(task.id)[:8]} was reported as failed by the robot"
            )
        elif task.status == TaskStatus.Successful:
            self.logger.info(
                f"{type(task).__name__} task: {str(task.id)[:8]} completed"
            )
        else:
            self.logger.info(
                f"Task: {str(task.id)[:8]} was reported as {task.status} by the robot"
            )

    def _get_mission_status_based_on_task_status(self) -> MissionStatus:
        fail_statuses = [
            TaskStatus.Cancelled,
            TaskStatus.Failed,
        ]
        partially_fail_statuses = fail_statuses + [TaskStatus.PartiallySuccessful]

        if len(self.tasks) == 0:
            return MissionStatus.Successful
        elif all(task.status in fail_statuses for task in self.tasks):
            return MissionStatus.Failed
        elif any(task.status in partially_fail_statuses for task in self.tasks):
            return MissionStatus.PartiallySuccessful
        else:
            return MissionStatus.Successful

    def _get_and_handle_task_status(self, current_task: TASKS) -> Optional[TASKS]:
        try:
            new_task_status = self._get_task_status(current_task.id)
        except RobotTaskStatusException as e:
            self.logger.error(
                "Failed to collect task status. Error description: %s",
                e.error_description,
            )
            # Currently we only stop mission monitoring after failing to get mission status
            return current_task

        if current_task.status != new_task_status:
            current_task.status = new_task_status
            self._log_task_status(current_task)
            publish_task_status(self.mqtt_publisher, current_task, self.mission_id)

        if is_finished(new_task_status):
            if should_upload_inspections(current_task):
                self.request_inspection_upload(current_task)
            current_task = get_next_task(self.task_iterator)
            if current_task is not None:
                # This is not required, but does make reporting more responsive
                current_task.status = TaskStatus.InProgress
                self._log_task_status(current_task)
                publish_task_status(self.mqtt_publisher, current_task, self.mission_id)
        return current_task

    def _handle_stopped_mission(self, current_task: Optional[TASKS]) -> None:
        if current_task is not None:
            current_task.status = TaskStatus.Cancelled
            publish_task_status(self.mqtt_publisher, current_task, self.mission_id)
        publish_mission_status(
            self.mqtt_publisher,
            self.mission_id,
            MissionStatus.Cancelled,
            self.error_message,
        )

    def run(self) -> None:

        self.task_iterator: Iterator[TASKS] = iter(self.tasks)
        current_task: Optional[TASKS] = get_next_task(self.task_iterator)
        current_task.status = TaskStatus.NotStarted
        current_mission_status = MissionStatus.NotStarted

        while True:
            if self.signal_thread_quitting.wait(0):
                return
            if self.signal_mission_stopped.wait(0):
                self._handle_stopped_mission(current_task)
                return

            if current_task:
                current_task = self._get_and_handle_task_status(current_task)

            new_mission_status: MissionStatus
            try:
                new_mission_status = self._get_mission_status(self.mission_id)
            except RobotMissionStatusException as e:
                self.logger.exception("Failed to collect mission status")
                self.error_message = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                current_task.status = TaskStatus.Failed
                publish_task_status(self.mqtt_publisher, current_task, self.mission_id)
                publish_mission_status(
                    self.mqtt_publisher,
                    self.mission_id,
                    MissionStatus.Failed,
                    self.error_message,
                )
                break

            if new_mission_status == MissionStatus.Cancelled or (
                new_mission_status
                not in [MissionStatus.NotStarted, MissionStatus.InProgress]
                and current_task is None  # We wait for all task statuses
            ):
                # Standardises final mission status report
                new_mission_status = self._get_mission_status_based_on_task_status()
                if self.error_message is None and new_mission_status in [
                    MissionStatus.Failed,
                    MissionStatus.Cancelled,
                ]:
                    self.error_message = ErrorMessage(
                        error_reason=None,
                        error_description="The mission failed because all tasks in the mission failed",
                    )
                publish_mission_status(
                    self.mqtt_publisher,
                    self.mission_id,
                    new_mission_status,
                    self.error_message,
                )
                break

            if new_mission_status != current_mission_status:
                current_mission_status = new_mission_status
                publish_mission_status(
                    self.mqtt_publisher,
                    self.mission_id,
                    current_mission_status,
                    self.error_message,
                )

            time.sleep(settings.FSM_SLEEP_TIME)

        self.logger.info("Stopped monitoring mission")
