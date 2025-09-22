from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from isar.state_machine.utils.common_event_handlers import (
    mission_started_event_handler,
    task_status_event_handler,
    task_status_failed_event_handler,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class GoingToLockdown(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _handle_task_completed(status: TaskStatus):
            if status != TaskStatus.Successful:
                state_machine.current_mission.error_message = ErrorMessage(
                    error_reason=ErrorReason.RobotActionException,
                    error_description="Lock down mission failed.",
                )
                return state_machine.lockdown_mission_failed  # type: ignore
            return state_machine.reached_lockdown  # type: ignore

        def _mission_failed_event_handler(
            event: Event[Optional[ErrorMessage]],
        ) -> Optional[Callable]:
            mission_failed: Optional[ErrorMessage] = event.consume_event()
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
                return state_machine.lockdown_mission_failed  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
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
                handler=_mission_failed_event_handler,
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
            state_name="going_to_lockdown",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
