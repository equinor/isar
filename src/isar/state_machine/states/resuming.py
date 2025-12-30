from typing import TYPE_CHECKING, List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Resuming(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _failed_resume_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[Paused.Paused]:
            return Paused.transition(mission_id)

        def _successful_resume_event_handler(
            successful_resume: bool,
        ) -> Transition[Monitor.Monitor]:
            return Monitor.transition(mission_id)

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
            state_name=States.Resuming,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission_id: str) -> Transition[Resuming]:
    def _transition(state_machine: "StateMachine"):
        return Resuming(state_machine, mission_id)

    return _transition
