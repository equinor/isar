from typing import TYPE_CHECKING, List

import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.state_machine.states_enum import States

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class PausingReturnHome(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="failed_pause_event",
                event=events.robot_service_events.mission_failed_to_pause,
                handler=lambda _: ReturningHome.transition_to_existing_mission(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="successful_pause_event",
                event=events.robot_service_events.mission_successfully_paused,
                handler=lambda _: ReturnHomePaused.transition(),
            ),
        ]
        super().__init__(
            state_name=States.PausingReturnHome,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[PausingReturnHome]:
    def _transition(state_machine: "StateMachine") -> PausingReturnHome:
        return PausingReturnHome(state_machine)

    return _transition
