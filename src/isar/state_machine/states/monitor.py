import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.services.utilities.threaded_request import ThreadedRequest
from isar.state_machine.utils.common_event_handlers import (
    mission_failed_event_handler,
    mission_started_event_handler,
    stop_mission_event_handler,
    task_status_event_handler,
    task_status_failed_event_handler,
)
from robot_interface.models.mission.status import TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        logger = logging.getLogger("state_machine")
        events = state_machine.events

        def _pause_mission_event_handler(event: Event[bool]) -> Optional[Callable]:
            if event.consume_event():
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
                event=events.api_requests.stop_mission.input,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
            ),
            EventHandlerMapping(
                name="pause_mission_event",
                event=events.api_requests.pause_mission.input,
                handler=_pause_mission_event_handler,
            ),
            EventHandlerMapping(
                name="mission_started_event",
                event=events.robot_service_events.mission_started,
                handler=lambda event: mission_started_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=lambda event: mission_failed_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="task_status_failed_event",
                event=events.robot_service_events.task_status_failed,
                handler=lambda event: task_status_failed_event_handler(
                    state_machine, _handle_task_completed, event
                ),
            ),
            EventHandlerMapping(
                name="task_status_event",
                event=events.robot_service_events.task_status_updated,
                handler=lambda event: task_status_event_handler(
                    state_machine, _handle_task_completed, event
                ),
            ),
        ]
        super().__init__(
            state_name="monitor",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
