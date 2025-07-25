import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.queues.events import Event
from isar.models.communication.queues.queue_utils import check_for_event
from isar.services.utilities.threaded_request import ThreadedRequest
from isar.state_machine.utils.generic_event_handlers import (
    check_and_handle_mission_failed_event,
    check_and_handle_mission_started_event,
    check_and_handle_stop_mission_event,
    check_and_handle_task_status_event,
    check_and_handle_task_status_failed_event,
)
from robot_interface.models.mission.status import TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def Monitor(
    state_machine: "StateMachine",
) -> EventHandlerBase:
    logger = logging.getLogger("state_machine")
    events = state_machine.events

    def _check_and_handle_pause_mission_event(event: Event[bool]) -> Optional[Callable]:
        if check_for_event(event):
            return state_machine.pause  # type: ignore
        return None

    def _handle_task_completed(task_status: TaskStatus):
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
            handler=lambda event: check_and_handle_stop_mission_event(
                state_machine, event
            ),
        ),
        EventHandlerMapping(
            name="pause_mission_event",
            eventQueue=events.api_requests.pause_mission.input,
            handler=_check_and_handle_pause_mission_event,
        ),
        EventHandlerMapping(
            name="mission_started_event",
            eventQueue=events.robot_service_events.mission_started,
            handler=lambda event: check_and_handle_mission_started_event(
                state_machine, event
            ),
        ),
        EventHandlerMapping(
            name="mission_failed_event",
            eventQueue=events.robot_service_events.mission_failed,
            handler=lambda event: check_and_handle_mission_failed_event(
                state_machine, event
            ),
        ),
        EventHandlerMapping(
            name="task_status_failed_event",
            eventQueue=events.robot_service_events.task_status_failed,
            handler=lambda event: check_and_handle_task_status_failed_event(
                state_machine, _handle_task_completed, event
            ),
        ),
        EventHandlerMapping(
            name="task_status_event",
            eventQueue=events.robot_service_events.task_status_updated,
            handler=lambda event: check_and_handle_task_status_event(
                state_machine, _handle_task_completed, event
            ),
        ),
    ]
    return EventHandlerBase(
        state_name="monitor",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
