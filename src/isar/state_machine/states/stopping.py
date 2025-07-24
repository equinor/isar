import logging
from queue import Queue
from typing import TYPE_CHECKING, Callable, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.communication.queues.queue_utils import check_for_event
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def Stopping(state_machine: "StateMachine"):
    logger = logging.getLogger("state_machine")
    events = state_machine.events

    def _check_and_handle_failed_stop(event: Queue[ErrorMessage]) -> Optional[Callable]:
        error_message: Optional[ErrorMessage] = check_for_event(event)
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

    def _check_and_handle_successful_stop(event: Queue[bool]) -> Optional[Callable]:
        if check_for_event(event):
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
            eventQueue=events.robot_service_events.mission_failed_to_stop,
            handler=_check_and_handle_failed_stop,
        ),
        EventHandlerMapping(
            name="successful_stop_event",
            eventQueue=events.robot_service_events.mission_successfully_stopped,
            handler=_check_and_handle_successful_stop,
        ),
    ]
    return EventHandlerBase(
        state_name="stopping",
        state_machine=state_machine,
        event_handler_mappings=event_handlers,
    )
