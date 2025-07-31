import logging
from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Stopping(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        logger = logging.getLogger("state_machine")
        events = state_machine.events

        def _failed_stop_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Callable]:
            error_message: Optional[ErrorMessage] = event.consume_event()
            if error_message is not None:
                logger.warning(error_message.error_description)
                if (
                    state_machine.current_mission is not None
                    and state_machine.current_mission._is_return_to_home_mission()
                ):
                    return state_machine.return_home_mission_stopping_failed  # type: ignore
                else:
                    return state_machine.mission_stopping_failed  # type: ignore
            return None

        def _successful_stop_event_handler(event: Event[bool]) -> Optional[Callable]:
            if event.consume_event():
                if (
                    state_machine.current_mission is not None
                    and state_machine.current_mission._is_return_to_home_mission()
                ):
                    return state_machine.return_home_mission_stopped  # type: ignore
                else:
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
            state_name="stopping",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
