import logging
import time
from threading import Event, Thread
from typing import Iterator, Optional

from isar.config.settings import settings
from isar.models.events import RobotServiceEvents
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
        robot_service_events: RobotServiceEvents,
        robot: RobotInterface,
        mqtt_publisher: MqttClientInterface,
        signal_thread_quitting: Event,
        signal_mission_stopped: Event,
        mission: Mission,
    ):
        self.logger = logging.getLogger("robot")
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.signal_mission_stopped: Event = signal_mission_stopped
        self.mqtt_publisher = mqtt_publisher
        self.current_mission: Optional[Mission] = mission

        Thread.__init__(self, name="Robot mission monitoring thread")

    def _get_task_status(self, task_id) -> TaskStatus:
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

    def _get_mission_status(self, mission_id) -> MissionStatus:
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

            except RobotMissionStatusException as e:
                failed_mission_error = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                break

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

    def _report_task_status(self, task: TASKS) -> None:
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

    def _finalize_mission_status(self):
        fail_statuses = [
            TaskStatus.Cancelled,
            TaskStatus.Failed,
        ]
        partially_fail_statuses = fail_statuses + [TaskStatus.PartiallySuccessful]

        if len(self.current_mission.tasks) == 0:
            self.current_mission.status = MissionStatus.Successful
        elif all(task.status in fail_statuses for task in self.current_mission.tasks):
            self.current_mission.error_message = ErrorMessage(
                error_reason=None,
                error_description="The mission failed because all tasks in the mission "
                "failed",
            )
            self.current_mission.status = MissionStatus.Failed
        elif any(
            task.status in partially_fail_statuses
            for task in self.current_mission.tasks
        ):
            self.current_mission.status = MissionStatus.PartiallySuccessful
        else:
            self.current_mission.status = MissionStatus.Successful

    def run(self) -> None:

        self.task_iterator: Iterator[TASKS] = iter(self.current_mission.tasks)
        current_task: Optional[TASKS] = get_next_task(self.task_iterator)
        current_task.status = TaskStatus.NotStarted

        last_mission_status: MissionStatus = MissionStatus.NotStarted

        while not self.signal_thread_quitting.wait(
            0
        ) or self.signal_mission_stopped.wait(0):

            if current_task:
                try:
                    new_task_status = self._get_task_status(current_task.id)
                except RobotTaskStatusException as e:
                    self.logger.error(
                        "Failed to collect task status. Error description: %s",
                        e.error_description,
                    )
                    break
                except Exception:
                    self.logger.exception("Failed to collect task status")
                    break

                if current_task.status != new_task_status:
                    current_task.status = new_task_status
                    self._report_task_status(current_task)
                    if settings.MQTT_ENABLED:
                        publish_task_status(
                            self.mqtt_publisher, current_task, self.current_mission
                        )

                if is_finished(new_task_status):
                    if should_upload_inspections(current_task):
                        self.robot_service_events.request_inspection_upload.trigger_event(
                            (current_task, self.current_mission)
                        )
                    current_task = get_next_task(self.task_iterator)
                    if current_task is not None:
                        # This is not required, but does make reporting more responsive
                        current_task.status = TaskStatus.InProgress
                        self._report_task_status(current_task)
                        if settings.MQTT_ENABLED:
                            publish_task_status(
                                self.mqtt_publisher, current_task, self.current_mission
                            )

            if self.signal_thread_quitting.wait(0) or self.signal_mission_stopped.wait(
                0
            ):
                break

            try:
                new_mission_status = self._get_mission_status(self.current_mission.id)
            except RobotMissionStatusException as e:
                self.logger.exception("Failed to collect mission status")
                self.robot_service_events.mission_failed.trigger_event(
                    ErrorMessage(
                        error_reason=e.error_reason,
                        error_description=e.error_description,
                    )
                )
                break
            if new_mission_status != last_mission_status:
                self.current_mission.status = new_mission_status
                last_mission_status = new_mission_status
                if settings.MQTT_ENABLED:
                    publish_mission_status(self.mqtt_publisher, self.current_mission)
                self.robot_service_events.mission_status_updated.trigger_event(
                    new_mission_status
                )

            if new_mission_status == MissionStatus.Cancelled or (
                new_mission_status
                not in [MissionStatus.NotStarted, MissionStatus.InProgress]
                and current_task is None
            ):
                # Standardises final mission status report
                mission_status = self.current_mission.status
                self._finalize_mission_status()
                if (
                    mission_status != self.current_mission.status
                    and settings.MQTT_ENABLED
                ):
                    publish_mission_status(self.mqtt_publisher, self.current_mission)
                break

            if self.signal_thread_quitting.wait(0) or self.signal_mission_stopped.wait(
                0
            ):
                break

            time.sleep(settings.FSM_SLEEP_TIME)

        mission_stopped = self.signal_mission_stopped.wait(0)

        if current_task:
            current_task.status = (
                TaskStatus.Cancelled if mission_stopped else TaskStatus.Failed
            )
            if settings.MQTT_ENABLED:
                publish_task_status(
                    self.mqtt_publisher, current_task, self.current_mission
                )
        if self.current_mission.status not in [
            MissionStatus.Cancelled,
            MissionStatus.PartiallySuccessful,
            MissionStatus.Failed,
            MissionStatus.Successful,
        ]:
            self.current_mission.status = MissionStatus.Cancelled
            if settings.MQTT_ENABLED:
                publish_mission_status(self.mqtt_publisher, self.current_mission)
            if not mission_stopped:
                self.robot_service_events.mission_status_updated.trigger_event(
                    self.current_mission.status
                )
        self.logger.info("Stopped monitoring mission")
