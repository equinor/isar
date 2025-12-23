from typing import TYPE_CHECKING, List, Optional

from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class PausingReturnHome(State):

    @staticmethod
    def transition() -> Transition["PausingReturnHome"]:
        def _transition(state_machine: "StateMachine"):
            return PausingReturnHome(state_machine)

        return _transition

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_pause_event_handler(
            event: Event[ErrorMessage],
        ) -> Optional[Transition[ReturningHome]]:
            error_message: Optional[ErrorMessage] = event.consume_event()

            if error_message is None:
                return None

            return ReturningHome.transition()

        def _successful_pause_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[ReturnHomePaused]]:
            if not event.consume_event():
                return None

            return ReturnHomePaused.transition()

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
            state_name=States.PausingReturnHome,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
