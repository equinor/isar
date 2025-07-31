from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import (
    mission_failed_event_handler,
    mission_started_event_handler,
    stop_mission_event_handler,
    task_status_event_handler,
    task_status_failed_event_handler,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ReturningHome(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _handle_task_completed(status: TaskStatus):
            if status != TaskStatus.Successful:
                state_machine.current_mission.error_message = ErrorMessage(
                    error_reason=ErrorReason.RobotActionException,
                    error_description="Return home failed.",
                )
                return state_machine.return_home_failed  # type: ignore
            return state_machine.returned_home  # type: ignore

        def _start_mission_event_handler(
            event: Event[Mission],
        ) -> Optional[Callable]:
            if event.has_event():
                return state_machine.stop  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="stop_mission_event",
                event=events.api_requests.stop_mission.input,
                handler=lambda event: stop_mission_event_handler(state_machine, event),
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
                name="start_mission_event",
                event=events.api_requests.start_mission.input,
                handler=_start_mission_event_handler,
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
            state_name="returning_home",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
