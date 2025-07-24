import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.queues.events import Event
from isar.models.communication.queues.queue_utils import check_for_event, trigger_event
from isar.services.utilities.threaded_request import ThreadedRequest
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import Task

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def Monitor(
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

    def _check_and_handle_stop_mission_event(event: Event[str]) -> Optional[Callable]:
        mission_id: str = check_for_event(event)
        if mission_id is not None:
            if state_machine.current_mission.id == mission_id or mission_id == "":
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

    def _check_and_handle_pause_mission_event(event: Event[bool]) -> Optional[Callable]:
        if check_for_event(event):
            return state_machine.pause  # type: ignore
        return None

    def _check_and_handle_mission_started_event(
        event: Event[bool],
    ) -> Optional[Callable]:
        if check_for_event(event):
            state_machine.mission_ongoing = True
        return None

    def _check_and_handle_mission_failed_event(
        event: Event[Optional[ErrorMessage]],
    ) -> Optional[Callable]:
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
            return state_machine.mission_failed_to_start  # type: ignore
        return None

    def _check_and_handle_task_status_failed_event(
        event: Event[Optional[ErrorMessage]],
    ) -> Optional[Callable]:
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

        elif (
            not state_machine.awaiting_task_status
            and state_machine.current_task is not None
        ):
            trigger_event(
                events.state_machine_events.task_status_request,
                state_machine.current_task.id,
            )
            state_machine.awaiting_task_status = True
        return None

    def _check_and_handle_task_status_event(
        event: Event[Optional[TaskStatus]],
    ) -> Optional[Callable]:
        if not state_machine.mission_ongoing:
            return None

        status: Optional[TaskStatus] = check_for_event(event)
        if status is not None:
            state_machine.awaiting_task_status = False
            return _handle_new_task_status(status)

        elif (
            not state_machine.awaiting_task_status
            and state_machine.current_task is not None
        ):
            trigger_event(
                events.state_machine_events.task_status_request,
                state_machine.current_task.id,
            )
            state_machine.awaiting_task_status = True
        return None

    def _handle_new_task_status(status: TaskStatus) -> Optional[Callable]:
        if state_machine.current_task is None:
            state_machine.iterate_current_task()

        state_machine.current_task.status = status

        if state_machine.current_task.is_finished():
            _report_task_status(state_machine.current_task)
            state_machine.publish_task_status(task=state_machine.current_task)

            if state_machine.should_upload_inspections():
                get_inspection_thread = ThreadedRequest(
                    state_machine.queue_inspections_for_upload
                )
                get_inspection_thread.start_thread(
                    deepcopy(state_machine.current_mission),
                    deepcopy(state_machine.current_task),
                    logger,
                    name="State Machine Get Inspections",
                )

            state_machine.iterate_current_task()
            if state_machine.current_task is None:
                return state_machine.mission_finished  # type: ignore
        return None

    event_handlers: List[EventHandlerMapping] = [
        EventHandlerMapping(
            name="stop_mission_event",
            eventQueue=events.api_requests.stop_mission.input,
            handler=_check_and_handle_stop_mission_event,
        ),
        EventHandlerMapping(
            name="pause_mission_event",
            eventQueue=events.api_requests.pause_mission.input,
            handler=_check_and_handle_pause_mission_event,
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
        state_name="monitor",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
