import logging
from queue import Queue
from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_for_event_without_consumption,
    trigger_event,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import Task

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def ReturningHome(
    state_machine: "StateMachine",
) -> EventHandlerBase:
    logger = logging.getLogger("state_machine")
    events = state_machine.events

    def _report_task_status(task: Task) -> None:
        if task.status == TaskStatus.Failed:
            logger.warning(
                f"Task: {str(task.id)[:8]} was reported as failed by the robot"
            )
        elif task.status == TaskStatus.Successful:
            logger.info(f"{type(task).__name__} task: {str(task.id)[:8]} completed")

    def _check_and_handle_stop_mission_event(event: Queue) -> Callable | None:
        mission_id: str = check_for_event(event)
        if mission_id is not None:
            if state_machine.current_mission.id == mission_id or mission_id == "":
                # TODO: this will bring us to an inconsistent state. We don't yet have a frozen state
                return state_machine.stop  # type: ignore
            else:
                events.api_requests.stop_mission.output.put(
                    ControlMissionResponse(
                        mission_id=mission_id,
                        mission_status=state_machine.current_mission.status,
                        mission_not_found=True,
                        task_id=state_machine.current_task.id,
                        task_status=state_machine.current_task.status,
                    )
                )
        return None

    def _check_and_handle_mission_started_event(event: Queue) -> Callable | None:
        if check_for_event(event):
            state_machine.mission_ongoing = True
        return None

    def _check_and_handle_mission_failed_event(event: Queue) -> Callable | None:
        mission_failed: Optional[ErrorMessage] = check_for_event(event)
        if mission_failed is not None:
            state_machine.logger.warning(
                f"Failed to initiate mission "
                f"{str(state_machine.current_mission.id)[:8]} because: "
                f"{mission_failed.error_description}"
            )
            state_machine.current_mission.error_message = ErrorMessage(
                error_reason=mission_failed.error_reason,
                error_description=mission_failed.error_description,
            )
            # TODO: this should lead us to retry going home, and if it keeps failing
            #       it should go to an error state
            return state_machine.mission_failed_to_start  # type: ignore
        return None

    def _check_and_handle_task_status_failed_event(event: Queue) -> Callable | None:
        if not state_machine.mission_ongoing:
            return None

        task_failure: Optional[ErrorMessage] = check_for_event(event)
        if task_failure is not None:
            state_machine.awaiting_task_status = False
            state_machine.current_task.error_message = task_failure
            logger.error(
                f"Monitoring task {state_machine.current_task.id[:8]} failed "
                f"because: {task_failure.error_description}"
            )
            return _handle_new_task_status(TaskStatus.Failed)

        elif not state_machine.awaiting_task_status:
            trigger_event(
                events.state_machine_events.task_status_request,
                state_machine.current_task.id,
            )
            state_machine.awaiting_task_status = True
        return None

    def _check_and_handle_task_status_event(event: Queue) -> Callable | None:
        if not state_machine.mission_ongoing:
            return None

        status: Optional[TaskStatus] = check_for_event(event)
        if status is not None:
            state_machine.awaiting_task_status = False
            return _handle_new_task_status(status)

        elif not state_machine.awaiting_task_status:
            trigger_event(
                events.state_machine_events.task_status_request,
                state_machine.current_task.id,
            )
            state_machine.awaiting_task_status = True
        return None

    def _handle_new_task_status(status: TaskStatus) -> Callable | None:
        if state_machine.current_task is None:
            state_machine.iterate_current_task()

        state_machine.current_task.status = status

        if state_machine.current_task.is_finished():
            _report_task_status(state_machine.current_task)
            state_machine.publish_task_status(task=state_machine.current_task)

            if status != TaskStatus.Successful:
                state_machine.current_mission.error_message = ErrorMessage(
                    error_reason=ErrorReason.RobotActionException,
                    error_description="Return home failed.",
                )
                return state_machine.return_home_failed  # type: ignore
            return state_machine.returned_home  # type: ignore
        return None

    def _check_and_handle_start_mission_event(
        event: Queue[StartMissionMessage],
    ) -> Callable | None:
        if check_for_event_without_consumption(event):
            return state_machine.stop  # type: ignore
        return None

    event_handlers: List[EventHandlerMapping] = [
        EventHandlerMapping(
            name="stop_mission_event",
            eventQueue=events.api_requests.stop_mission.input,
            handler=_check_and_handle_stop_mission_event,
        ),
        EventHandlerMapping(
            name="mission_started_event",
            eventQueue=events.robot_service_events.mission_started,
            handler=_check_and_handle_mission_started_event,
        ),
        EventHandlerMapping(
            name="mission_failed_event",
            eventQueue=events.robot_service_events.mission_failed,
            handler=_check_and_handle_mission_failed_event,
        ),
        EventHandlerMapping(
            name="start_mission_event",
            eventQueue=events.api_requests.start_mission.input,
            handler=_check_and_handle_start_mission_event,
        ),
        EventHandlerMapping(
            name="task_status_failed_event",
            eventQueue=events.robot_service_events.task_status_failed,
            handler=_check_and_handle_task_status_failed_event,
        ),
        EventHandlerMapping(
            name="task_status_event",
            eventQueue=events.robot_service_events.task_status_updated,
            handler=_check_and_handle_task_status_event,
        ),
    ]
    return EventHandlerBase(
        state_name="returning_home",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
