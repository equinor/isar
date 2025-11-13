from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import MaintenanceResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingDueToMaintenance(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is not None:
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(
                        is_maintenance_mode=False,
                        failure_reason="Failed to stop ongoing mission",
                    )
                )
                state_machine.logger.error(
                    f"Failed to stop mission in StoppingDueToMaintenance. Message: {error_message.error_description}"
                )
                return state_machine.mission_stopping_failed  # type: ignore
            return None

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if event.consume_event():
                state_machine.publish_mission_aborted(
                    "Mission aborted, robot being sent to maintenance", True
                )
                events.api_requests.set_maintenance_mode.response.trigger_event(
                    MaintenanceResponse(is_maintenance_mode=True)
                )
                return state_machine.mission_stopped  # type: ignore
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_stop_event",
                event=events.robot_service_events.mission_failed_to_stop,
                handler=_failed_stop_event_handler,
            ),
            EventHandlerMapping(
                name="successful_stop_event",
                event=events.robot_service_events.mission_successfully_stopped,
                handler=_successful_stop_event_handler,
            ),
        ]
        super().__init__(
            state_name="stopping_due_to_maintenance",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
