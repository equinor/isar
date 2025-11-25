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

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is None:
                return None

            stopped_mission_response: ControlMissionResponse = ControlMissionResponse(
                success=False, failure_reason="ISAR failed to stop mission"
            )
            state_machine.events.api_requests.stop_mission.response.trigger_event(
                stopped_mission_response
            )
            return state_machine.mission_stopping_failed  # type: ignore

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            state_machine.events.api_requests.stop_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )

            if state_machine.shared_state.mission_id.check() is None:
                reason: str = (
                    "Robot was busy and mission stopped but no ongoing mission found in shared state."
                )
                state_machine.logger.warning(reason)
                state_machine.publish_mission_aborted(reason, False)

            state_machine.print_transitions()
            if not state_machine.battery_level_is_above_mission_start_threshold():
                state_machine.start_return_home_mission()
                return state_machine.start_return_home_monitoring  # type: ignore
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
