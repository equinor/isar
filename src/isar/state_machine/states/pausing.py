from typing import TYPE_CHECKING, List

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Pausing(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _failed_pause_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[Monitor.Monitor]:
            return Monitor.transition(mission_id)

        def _successful_pause_event_handler(
            successful_pause: bool,
        ) -> Transition[Paused.Paused]:
            return Paused.transition(mission_id)

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
            state_name=States.Pausing,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition(mission_id: str) -> Transition[Pausing]:
    def _transition(state_machine: "StateMachine"):
        return Pausing(state_machine, mission_id=mission_id)

    return _transition
