from typing import TYPE_CHECKING, List

import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ResumingReturnHome(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _failed_resume_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[ReturnHomePaused.ReturnHomePaused]:
            return ReturnHomePaused.transition()

        def _successful_resume_event_handler(
            successful_resume: bool,
        ) -> Transition[ReturningHome.ReturningHome]:
            return ReturningHome.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="failed_resume_event",
                event=events.robot_service_events.mission_failed_to_resume,
                handler=_failed_resume_event_handler,
            ),
            EventHandlerMapping(
                name="successful_resume_event",
                event=events.robot_service_events.mission_successfully_resumed,
                handler=_successful_resume_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.ResumingReturnHome,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[ResumingReturnHome]:
    def _transition(state_machine: "StateMachine"):
        return ResumingReturnHome(state_machine)

    return _transition
