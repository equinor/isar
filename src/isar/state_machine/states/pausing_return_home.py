from typing import TYPE_CHECKING, List

import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class PausingReturnHome(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_pause_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[ReturningHome.ReturningHome]:
            return ReturningHome.transition()

        def _successful_pause_event_handler(
            successful_pause: bool,
        ) -> Transition[ReturnHomePaused.ReturnHomePaused]:
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


def transition() -> Transition[PausingReturnHome]:
    def _transition(state_machine: "StateMachine"):
        return PausingReturnHome(state_machine)

    return _transition
