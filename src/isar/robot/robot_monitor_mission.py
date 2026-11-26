import asyncio
import logging
from collections.abc import Callable, Iterator

from isar.config.settings import settings
from isar.models.mqtt_queue import MQTTQueue
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
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


def get_next_task(task_iterator: Iterator[TASKS]) -> TASKS | None:
    try:
        return next(task_iterator)
    except StopIteration:
        return None


def is_finished(task_status: TaskStatus) -> bool:
    return (
        task_status == TaskStatus.Successful
        or task_status == TaskStatus.Cancelled
        or task_status == TaskStatus.Failed
    )


def should_upload_inspections(task: TASKS) -> bool:
    if settings.UPLOAD_INSPECTIONS_ASYNC:
        return False

    return task.status == TaskStatus.Successful and isinstance(task, InspectionTask)


async def get_task_status(
    robot: RobotInterface,
    task_id: str,
) -> TaskStatus:
    task_status: TaskStatus = TaskStatus.NotStarted
    failed_task_error: ErrorMessage | None = None
    request_status_failure_counter: int = 0

    while (
        request_status_failure_counter < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
    ):
        if request_status_failure_counter > 0:
            await asyncio.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

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

        return task_status

    assert failed_task_error is not None
    raise RobotTaskStatusException(
        error_description=failed_task_error.error_description
    )


async def get_mission_status(
    robot: RobotInterface,
    mission_id: str,
) -> MissionStatus:
    mission_status: MissionStatus = MissionStatus.NotStarted
    failed_mission_error: ErrorMessage | None = None
    request_status_failure_counter: int = 0

    while (
        request_status_failure_counter < settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
    ):
        if request_status_failure_counter > 0:
            await asyncio.sleep(settings.REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY)

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

        return mission_status

    raise RobotMissionStatusException(
        error_description=(
            failed_mission_error.error_description
            if failed_mission_error
            else "Mission status thread cancelled"
        )
    )


async def get_and_report_task_status(
    current_task: TASKS,
    robot: RobotInterface,
    mission_id: str,
    mqtt_queue: MQTTQueue,
) -> TaskStatus:
    logger = logging.getLogger("robot")
    new_task_status: TaskStatus | None = None
    try:
        new_task_status = await get_task_status(robot, current_task.id)

        if current_task.status != new_task_status:
            current_task.status = new_task_status
            logger.info(
                f"Task: {type(current_task).__name__} task: {str(current_task.id)[:8]} reported as {current_task.status} by the robot"
            )
            mqtt_queue.publish_task_status(current_task, mission_id)
        return new_task_status

    except RobotTaskStatusException as e:
        logger.error(
            "Failed to collect task status. Error description: %s",
            e.error_description,
        )
        return None


async def robot_monitor_return_home_mission(
    mission_id: str,
    robot: RobotInterface,
) -> tuple[ErrorMessage | None, bool]:
    logger = logging.getLogger("robot")
    logger.info("Started monitoring return home mission")
    error_message: ErrorMessage | None = None

    mission_status: MissionStatus = MissionStatus.InProgress
    try:
        while mission_status in [
            MissionStatus.NotStarted,
            MissionStatus.InProgress,
            MissionStatus.Paused,
        ]:
            try:
                mission_status = await get_mission_status(robot, mission_id)
            except RobotMissionStatusException as e:
                logger.exception("Failed to collect mission status")
                error_message = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )
                mission_status = MissionStatus.Failed

            await asyncio.sleep(settings.FSM_SLEEP_TIME)

        if error_message is None and mission_status in [
            MissionStatus.Failed,
            MissionStatus.Cancelled,
        ]:
            error_message = ErrorMessage(
                error_reason=None,
                error_description="The mission was reported as failed by the robot",
            )
        return error_message, False
    except asyncio.CancelledError:
        return None, True
    finally:
        logger.info("Stopped monitoring return home mission")


async def _poll_mission_status(
    robot: RobotInterface,
    mission_id: str,
) -> tuple[MissionStatus, ErrorMessage | None]:
    logger = logging.getLogger("robot")
    try:
        return await get_mission_status(robot, mission_id), None
    except RobotMissionStatusException as e:
        logger.exception("Failed to collect mission status")
        return (
            MissionStatus.Failed,
            ErrorMessage(
                error_reason=e.error_reason,
                error_description=e.error_description,
            ),
        )


async def _advance_task(
    current_task: TASKS,
    task_iterator: Iterator[TASKS],
    robot: RobotInterface,
    mission_id: str,
    request_inspection_upload: Callable[[InspectionTask], None],
    mqtt_queue: MQTTQueue,
) -> TASKS | None:
    task_status = await get_and_report_task_status(
        current_task,
        robot,
        mission_id,
        mqtt_queue,
    )
    if task_status is None:
        # Currently we only stop mission monitoring after failing to get mission status
        return None
    if is_finished(task_status):
        if should_upload_inspections(current_task):
            request_inspection_upload(current_task)  # type: ignore
        return get_next_task(task_iterator)
    return current_task


async def robot_monitor_mission(
    mission: Mission,
    robot: RobotInterface,
    request_inspection_upload: Callable[[InspectionTask], None],
    mqtt_queue: MQTTQueue,
) -> tuple[ErrorMessage | None, Mission, bool]:
    logger = logging.getLogger("robot")
    logger.info(f"Started monitoring mission {mission.name}")
    error_message: ErrorMessage | None = None

    task_iterator: Iterator[TASKS] = iter(mission.tasks)
    current_task: TASKS | None = get_next_task(task_iterator)
    if current_task is not None:
        current_task.status = TaskStatus.NotStarted

    mission_status: MissionStatus = MissionStatus.InProgress
    try:
        while mission_status in [
            MissionStatus.NotStarted,
            MissionStatus.InProgress,
            MissionStatus.Paused,
        ]:
            mission_status, error_message = await _poll_mission_status(
                robot, mission.id
            )
            if mission_status not in [
                MissionStatus.NotStarted,
                MissionStatus.InProgress,
                MissionStatus.Paused,
            ]:
                break

            if current_task is not None:
                current_task = await _advance_task(
                    current_task,
                    task_iterator,
                    robot,
                    mission.id,
                    request_inspection_upload,
                    mqtt_queue,
                )

            await asyncio.sleep(settings.FSM_SLEEP_TIME)

        if mission_status == MissionStatus.Successful:
            while current_task is not None:
                current_task = await _advance_task(
                    current_task,
                    task_iterator,
                    robot,
                    mission.id,
                    request_inspection_upload,
                    mqtt_queue,
                )
                if current_task is not None:
                    await asyncio.sleep(settings.FSM_SLEEP_TIME)
        elif mission_status in [MissionStatus.Failed, MissionStatus.Cancelled]:
            if current_task is not None:
                current_task.status = (
                    TaskStatus.Cancelled
                    if mission_status == MissionStatus.Cancelled
                    else TaskStatus.Failed
                )
                mqtt_queue.publish_task_status(current_task, mission.id)
            if error_message is None:
                error_message = ErrorMessage(
                    error_reason=None,
                    error_description=(
                        f"Stored mission reported as {mission_status.value} by the robot"
                        if not mission.tasks
                        else "The mission was reported as failed by the robot"
                    ),
                )

        return error_message, mission, False
    except asyncio.CancelledError:
        if current_task is not None:
            current_task.status = TaskStatus.Cancelled
            mqtt_queue.publish_task_status(current_task, mission.id)
        return None, mission, True
    finally:
        logger.info("Stopped monitoring mission")
