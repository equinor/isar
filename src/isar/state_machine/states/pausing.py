import logging
from isar.models.events import Event
from typing import TYPE_CHECKING, Callable, List, Optional
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Pausing(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        logger = logging.getLogger("state_machine")
        events = state_machine.events

        def _failed_pause_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is not None:
                logger.warning(error_message.error_description)
                return state_machine.mission_pausing_failed
            return None

        def _successful_pause_event_handler(event: Event[bool]) -> Optional[Callable]:
            if event.consume_event():
                return state_machine.paused_state
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_pause_event",
                event=events.robot_service_events.mission_failed_to_pause,
                handler=_failed_pause_event_handler,
            ),
            EventHandlerMapping(
                name="successful_pause_event",
                event=events.robot_service_events.mission_successfully_paused,
                handler=_successful_pause_event_handler,
            ),
        ]
        super().__init__(
            state_name="paused",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
