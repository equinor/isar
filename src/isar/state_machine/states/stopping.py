from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import ControlMissionResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stopping(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _stop_mission_cleanup() -> None:
            state_machine.events.api_requests.stop_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )
            state_machine.print_transitions()
            return None

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is None:
                return None

            return state_machine.mission_stopping_failed  # type: ignore

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            _stop_mission_cleanup()
            if not state_machine.battery_level_is_above_mission_start_threshold():
                return state_machine.request_return_home  # type: ignore
            return state_machine.mission_stopped  # type: ignore

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
            state_name="stopping",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
