import logging
import time
from threading import Event
from typing import Callable, Iterator, List, Optional

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


def get_next_task(task_iterator: Iterator[TASKS]) -> TASKS | None:
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


def get_task_status(
    signal_exit: Event,
    signal_mission_stopped: Event,
    robot: RobotInterface,
    task_id: str,
) -> TaskStatus:
    task_status: TaskStatus = TaskStatus.NotStarted
    failed_task_error: Optional[ErrorMessage] = None
    request_status_failure_counter: int = 0

    while (
        request_status_failure_counter < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
    ):
        if signal_exit.wait(0) or signal_mission_stopped.wait(0):
            return TaskStatus.Cancelled
        if request_status_failure_counter > 0:
            time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

        try:
            task_status = robot.task_status(task_id)
            request_status_failure_counter = 0
        except (
            RobotCommunicationTimeoutException,
            RobotCommunicationException,
        ) as e:
            request_status_failure_counter += 1
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

    assert failed_task_error is not None
    raise RobotTaskStatusException(
        error_description=failed_task_error.error_description
    )


def get_mission_status(
    signal_exit: Event,
    signal_mission_stopped: Event,
    robot: RobotInterface,
    mission_id: str,
) -> MissionStatus:
    mission_status: MissionStatus = MissionStatus.NotStarted
    failed_mission_error: Optional[ErrorMessage] = None
    request_status_failure_counter: int = 0

    while (
        request_status_failure_counter < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
    ):
        if signal_exit.wait(0) or signal_mission_stopped.wait(0):
            break
        if request_status_failure_counter > 0:
            time.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

        try:
            mission_status = robot.mission_status(mission_id)
            request_status_failure_counter = 0
        except (
            RobotCommunicationTimeoutException,
            RobotCommunicationException,
        ) as e:
            request_status_failure_counter += 1
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


def log_task_status(logger: logging.Logger, task: TASKS) -> None:
    if task.status == TaskStatus.Failed:
        logger.warning(f"Task: {str(task.id)[:8]} was reported as failed by the robot")
    elif task.status == TaskStatus.Successful:
        logger.info(f"{type(task).__name__} task: {str(task.id)[:8]} completed")
    else:
        logger.info(
            f"Task: {str(task.id)[:8]} was reported as {task.status} by the robot"
        )


def get_mission_status_based_on_task_status(tasks: List[TASKS]) -> MissionStatus:
    fail_statuses = [
        TaskStatus.Cancelled,
        TaskStatus.Failed,
    ]
    partially_fail_statuses = fail_statuses + [TaskStatus.PartiallySuccessful]

    if len(tasks) == 0:
        return MissionStatus.Successful
    elif all(task.status in fail_statuses for task in tasks):
        return MissionStatus.Failed
    elif any(task.status in partially_fail_statuses for task in tasks):
        return MissionStatus.PartiallySuccessful
    else:
        return MissionStatus.Successful


def robot_monitor_mission(
    mission: Mission,
    signal_exit: Event,
    signal_mission_stopped: Event,
    robot: RobotInterface,
    request_inspection_upload: Callable[[InspectionTask], None],
    mqtt_publisher: MqttClientInterface,
) -> None | ErrorMessage:
    logger = logging.getLogger("robot")
    error_message: Optional[ErrorMessage] = None

    task_iterator: Iterator[TASKS] = iter(mission.tasks)
    current_task: Optional[TASKS] = get_next_task(task_iterator)
    current_task.status = TaskStatus.NotStarted  # type: ignore
    current_mission_status = MissionStatus.NotStarted

    while True:
        if signal_exit.wait(0):
            return None
        if signal_mission_stopped.wait(0):
            if current_task is not None:
                current_task.status = TaskStatus.Cancelled
                publish_task_status(mqtt_publisher, current_task, mission.id)
            publish_mission_status(
                mqtt_publisher,
                mission.id,
                MissionStatus.Cancelled,
                ErrorMessage(
                    ErrorReason.RobotMissionStatusException, "Mission cancelled"
                ),
            )
            return None

        if current_task:
            new_task_status: TaskStatus | None = None
            try:
                new_task_status = get_task_status(
                    signal_exit, signal_mission_stopped, robot, current_task.id
                )

                if current_task.status != new_task_status:
                    current_task.status = new_task_status
                    log_task_status(logger, current_task)
                    publish_task_status(mqtt_publisher, current_task, mission.id)

                if is_finished(new_task_status):
                    if should_upload_inspections(current_task):
                        request_inspection_upload(current_task)  # type: ignore
                    current_task = get_next_task(task_iterator)
                    if current_task is not None:
                        # This is not required, but does make reporting more responsive
                        current_task.status = TaskStatus.InProgress
                        log_task_status(logger, current_task)
                        publish_task_status(mqtt_publisher, current_task, mission.id)
            except RobotTaskStatusException as e:
                logger.error(
                    "Failed to collect task status. Error description: %s",
                    e.error_description,
                )
                # Currently we only stop mission monitoring after failing to get mission status

        new_mission_status: MissionStatus
        try:
            new_mission_status = get_mission_status(
                signal_exit, signal_mission_stopped, robot, mission.id
            )
        except RobotMissionStatusException as e:
            logger.exception("Failed to collect mission status")
            error_message = ErrorMessage(
                error_reason=e.error_reason,
                error_description=e.error_description,
            )
            if current_task:
                current_task.status = TaskStatus.Failed
                publish_task_status(mqtt_publisher, current_task, mission.id)
            publish_mission_status(
                mqtt_publisher,
                mission.id,
                MissionStatus.Failed,
                error_message,
            )
            break

        if new_mission_status == MissionStatus.Cancelled or (
            new_mission_status
            not in [MissionStatus.NotStarted, MissionStatus.InProgress]
            and current_task is None  # We wait for all task statuses
        ):
            if (
                new_mission_status == MissionStatus.Cancelled
                and current_task is not None
                and current_task.status == TaskStatus.InProgress
            ):
                current_task.status = TaskStatus.Cancelled
                publish_task_status(mqtt_publisher, current_task, mission.id)

            # Standardises final mission status report
            new_mission_status = get_mission_status_based_on_task_status(mission.tasks)
            if error_message is None and new_mission_status in [
                MissionStatus.Failed,
                MissionStatus.Cancelled,
            ]:
                error_message = ErrorMessage(
                    error_reason=None,
                    error_description="The mission failed because all tasks in the mission failed",
                )
            publish_mission_status(
                mqtt_publisher,
                mission.id,
                new_mission_status,
                error_message,
            )
            break

        if new_mission_status != current_mission_status:
            current_mission_status = new_mission_status
            publish_mission_status(
                mqtt_publisher,
                mission.id,
                current_mission_status,
                error_message,
            )

        time.sleep(settings.FSM_SLEEP_TIME)

    logger.info("Stopped monitoring mission")
    return error_message
