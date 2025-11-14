from typing import TYPE_CHECKING, Callable, List, Optional

from isar.apis.models.models import LockdownResponse
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class StoppingGoToLockdown(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is None:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(
                    lockdown_started=False,
                    failure_reason="Failed to stop ongoing mission",
                )
            )
            return state_machine.mission_stopping_failed  # type: ignore

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if not event.consume_event():
                return None

            state_machine.publish_mission_aborted("Robot being sent to lockdown", True)

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            state_machine.start_return_home_mission()
            return state_machine.start_lockdown_mission_monitoring  # type: ignore

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
            state_name="stopping_go_to_lockdown",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
